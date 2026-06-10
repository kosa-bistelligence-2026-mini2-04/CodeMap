from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

from app.guardrail.validator import GuardrailValidator
from app.llm.provider import BudgetExhaustedError
from app.models.agent_schemas import (
    BehaviorInfererInput,
    CommunityAssessorInput,
    CommunityResult,
    ReporterInput,
    StaticAnalyzerInput,
)
from app.models.api_schemas import GuardrailTelemetry, PartialReporterInput, ReportJsonResponse
from app.orchestrator.timeout_guard import TimeoutGuard

if TYPE_CHECKING:
    from app.agents.behavior_inferer import BehaviorInferer
    from app.agents.community_assessor import CommunityAssessor
    from app.agents.emergency_reporter import EmergencyReporter
    from app.agents.reporter import Reporter
    from app.agents.static_analyzer import StaticAnalyzer
    from app.api.progress_bus import ProgressBus
    from app.services.observability import ObservabilityCollector
    from app.services.repo_cloner import RepoCloner

BUDGET_TOTAL_S = 120
# Per-agent budgets. Static / Behavior / Community run concurrently, so the
# parallel-phase wall clock = max(static, behavior, community). The remaining
# headroom covers Planner orchestration overhead (clone, RepoMap build,
# conflict resolver LLM judge, guardrail pass) + Reporter's LLM executive
# summary. Math: max(85, 85, 60) + 20 = 105s + ~15s overhead budget = 120s.
BUDGET_STATIC_S = 85
BUDGET_BEHAVIOR_S = 85
BUDGET_COMMUNITY_S = 60
BUDGET_REPORTER_S = 20


class PipelineBudgetExhausted(Exception):
    """Raised ONLY when outer wait_for total budget timer fires."""


async def _publish(bus: "ProgressBus | None", job_id: str, event: dict) -> None:
    if bus is not None:
        try:
            await bus.publish(job_id, event)
        except Exception:
            pass


# Per-agent sub-stage labels for fine-grained progress display.
# Each tuple is (elapsed_frac_lower_bound, progress_percent, chinese_label).
_AGENT_TICKER_STAGES = {
    "static_analyzer": [
        (0.00, 15, "扫描仓库文件..."),
        (0.15, 30, "pylint 复杂度分析..."),
        (0.45, 55, "radon 可维护性评分..."),
        (0.70, 75, "覆盖率映射..."),
        (0.88, 90, "生成热力图..."),
    ],
    "behavior_inferer": [
        (0.00, 15, "加载 README / Issue 模板..."),
        (0.08, 25, "构建 RepoMap 索引..."),
        (0.18, 35, "拼装 LLM Prompt..."),
        (0.28, 50, "LLM 推理中..."),
        (0.55, 70, "LLM 生成 JSON..."),
        (0.82, 85, "Guardrail 双层过滤..."),
    ],
    "community_assessor": [
        (0.00, 20, "解析 git log..."),
        (0.45, 55, "聚合贡献者..."),
        (0.75, 85, "查询 Issue 响应时间..."),
    ],
    "reporter": [
        (0.00, 25, "聚合三 Agent 结果..."),
        (0.35, 55, "冲突消解..."),
        (0.60, 75, "生成 HTML + 热力图..."),
        (0.85, 92, "Self-check 自洽检查..."),
    ],
}


async def _agent_progress_ticker(
    bus: "ProgressBus | None",
    job_id: str,
    agent_name: str,
    budget_s: float,
    interval: float = 1.2,
) -> None:
    """Emit periodic agent_status events with stage_label during an agent run.

    Runs until cancelled. Picks the right stage_label based on elapsed/budget.
    """
    if bus is None:
        return
    stages = _AGENT_TICKER_STAGES.get(agent_name, [])
    if not stages:
        return
    started = asyncio.get_event_loop().time()
    try:
        while True:
            elapsed = asyncio.get_event_loop().time() - started
            frac = min(0.95, elapsed / max(budget_s, 0.1))
            # Pick the deepest stage whose lower bound <= frac
            current = stages[0]
            for stage in stages:
                if frac >= stage[0]:
                    current = stage
                else:
                    break
            # Linear interpolation between this stage and next one (if any) for
            # smoother numeric progress while label stays on the current stage.
            idx = stages.index(current)
            if idx + 1 < len(stages):
                next_stage = stages[idx + 1]
                span = max(0.001, next_stage[0] - current[0])
                within = (frac - current[0]) / span
                interp_progress = int(current[1] + within * (next_stage[1] - current[1]))
            else:
                interp_progress = current[1]
            await _publish(bus, job_id, {
                "type": "agent_status",
                "agent": agent_name,
                "status": "running",
                "progress": max(10, min(95, interp_progress)),
                "stage_label": current[2],
            })
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        pass


async def _handle_community(
    result: CommunityResult | BaseException,
    job_id: str,
    repo_path: str,
    timeout_guard: TimeoutGuard,
    bus: "ProgressBus | None" = None,
) -> CommunityResult:
    if isinstance(result, asyncio.CancelledError):
        raise result
    if isinstance(result, (TimeoutError, asyncio.TimeoutError)):
        await _publish(bus, job_id, {
            "type": "degraded",
            "agent": "community_assessor",
            "reason": "exceeded 45s budget",
        })
        return await timeout_guard.get_degraded_community(job_id, repo_path)
    if isinstance(result, BaseException):
        await _publish(bus, job_id, {
            "type": "degraded",
            "agent": "community_assessor",
            "reason": f"unexpected_error: {type(result).__name__}",
        })
        return await timeout_guard.get_degraded_community(job_id, repo_path)
    return result


def _unwrap_or_raise(result: object, agent_name: str):
    if isinstance(result, BaseException):
        raise result
    return result


async def _load_readme(cloned_path: str) -> str:
    import glob as _glob
    import os
    readme_matches = sorted(_glob.glob(os.path.join(cloned_path, "README*")))
    if not readme_matches:
        return ""
    try:
        return Path(readme_matches[0]).read_text(encoding="utf-8", errors="replace")[:8000]
    except OSError:
        return ""


class Planner:
    """Main orchestrator: schedules agents concurrently, enforces timeouts, resolves conflicts."""

    def __init__(
        self,
        static_analyzer: "StaticAnalyzer | None" = None,
        behavior_inferer: "BehaviorInferer | None" = None,
        community_assessor: "CommunityAssessor | None" = None,
        reporter: "Reporter | None" = None,
        emergency_reporter: "EmergencyReporter | None" = None,
        repo_cloner: "RepoCloner | None" = None,
        guardrail: GuardrailValidator | None = None,
        timeout_guard: TimeoutGuard | None = None,
        progress_bus: "ProgressBus | None" = None,
        observability: "ObservabilityCollector | None" = None,
    ) -> None:
        self.static_analyzer = static_analyzer
        self.behavior_inferer = behavior_inferer
        self.community_assessor = community_assessor
        self.reporter = reporter
        self.repo_cloner = repo_cloner
        self.guardrail = guardrail or GuardrailValidator()
        self.timeout_guard = timeout_guard or TimeoutGuard()
        self.progress_bus = progress_bus
        self.observability = observability

        if emergency_reporter is None:
            from app.agents.emergency_reporter import EmergencyReporter as _ER
            self.emergency_reporter: "EmergencyReporter" = _ER()
        else:
            self.emergency_reporter = emergency_reporter

    def _build_partial_from_current_state(self, job_id: str) -> PartialReporterInput:
        return PartialReporterInput(job_id=job_id)

    async def run_pipeline(
        self,
        job_id: str,
        source: str,
        path: str,
        force_refresh: bool = False,
        model_override: str | None = None,
    ) -> ReportJsonResponse:
        try:
            return await self._outer_wait(job_id, source, path, force_refresh, model_override)
        except PipelineBudgetExhausted:
            partial = self._build_partial_from_current_state(job_id)
            return await self.emergency_reporter.render(partial, "planner_budget_exhausted")
        except BudgetExhaustedError:
            partial = self._build_partial_from_current_state(job_id)
            return await self.emergency_reporter.render(partial, "planner_budget_exhausted")

    async def _outer_wait(
        self,
        job_id: str,
        source: str,
        path: str,
        force_refresh: bool = False,
        model_override: str | None = None,
    ) -> ReportJsonResponse:
        try:
            return await asyncio.wait_for(
                self._run_pipeline_inner(job_id, source, path, force_refresh, model_override),
                timeout=BUDGET_TOTAL_S,
            )
        except asyncio.TimeoutError:
            raise PipelineBudgetExhausted()

    async def _run_pipeline_inner(
        self,
        job_id: str,
        source: str,
        path: str,
        force_refresh: bool = False,
        model_override: str | None = None,
    ) -> ReportJsonResponse:
        t_start = time.monotonic()
        cloned_path: str | None = None

        try:
            await _publish(self.progress_bus, job_id, {"type": "stage", "stage": "clone", "status": "running"})
            cloned_path = await self.repo_cloner.clone(source, path, job_id)
            await _publish(self.progress_bus, job_id, {"type": "stage", "stage": "clone", "status": "completed"})

            await _publish(self.progress_bus, job_id, {"type": "stage", "stage": "analysis", "status": "running"})

            # U-1 fix: emit per-agent running events up front so ProgressPanel
            # advances from 0% as soon as gather kicks off.
            for _ag, _label in [
                ("static_analyzer", "扫描仓库文件..."),
                ("behavior_inferer", "加载 README / Issue 模板..."),
                ("community_assessor", "解析 git log..."),
            ]:
                await _publish(self.progress_bus, job_id, {
                    "type": "agent_status",
                    "agent": _ag,
                    "status": "running",
                    "progress": 10,
                    "stage_label": _label,
                })

            # Spawn fine-grained progress tickers so the frontend sees real
            # periodic progress updates (every ~1.2s) with Chinese stage labels
            # instead of a single 10% → 100% jump.
            static_ticker = asyncio.create_task(
                _agent_progress_ticker(
                    self.progress_bus, job_id, "static_analyzer", BUDGET_STATIC_S
                )
            )
            behavior_ticker = asyncio.create_task(
                _agent_progress_ticker(
                    self.progress_bus, job_id, "behavior_inferer", BUDGET_BEHAVIOR_S
                )
            )
            community_ticker = asyncio.create_task(
                _agent_progress_ticker(
                    self.progress_bus, job_id, "community_assessor", BUDGET_COMMUNITY_S
                )
            )

            static_task = asyncio.create_task(
                asyncio.wait_for(
                    self.static_analyzer.run(
                        StaticAnalyzerInput(
                            repo_path=cloned_path,
                            job_id=job_id,
                        )
                    ),
                    timeout=BUDGET_STATIC_S,
                )
            )
            behavior_task = asyncio.create_task(
                asyncio.wait_for(
                    self.behavior_inferer.infer(
                        BehaviorInfererInput(
                            repo_path=cloned_path,
                            job_id=job_id,
                            source_url=path,
                            force_refresh=force_refresh,
                            llm_model=model_override or "gpt-5.4",
                        )
                    ),
                    timeout=BUDGET_BEHAVIOR_S,
                )
            )
            community_task = asyncio.create_task(
                asyncio.wait_for(
                    self.community_assessor.run(
                        CommunityAssessorInput(
                            repo_path=cloned_path,
                            job_id=job_id,
                        )
                    ),
                    timeout=BUDGET_COMMUNITY_S,
                )
            )

            results = await asyncio.gather(
                static_task,
                behavior_task,
                community_task,
                return_exceptions=True,
            )

            # Stop tickers now that real results are in. CancelledError is
            # the expected happy path; a real Exception means the ticker
            # coroutine itself crashed (logic bug) — log it but never bubble
            # up so pipeline keeps running.
            for _t in (static_ticker, behavior_ticker, community_ticker):
                _t.cancel()
            for _t in (static_ticker, behavior_ticker, community_ticker):
                try:
                    await _t
                except asyncio.CancelledError:
                    pass  # expected cancellation, not an error
                except Exception:
                    logger.exception("agent progress ticker crashed")

            if isinstance(results[0], BaseException):
                await _publish(self.progress_bus, job_id, {
                    "type": "degraded",
                    "agent": "static_analyzer",
                    "reason": f"failed: {type(results[0]).__name__}",
                })
                partial = PartialReporterInput(job_id=job_id)
                return await self.emergency_reporter.render(partial, "static_analyzer_failed")

            static_result = results[0]
            await _publish(self.progress_bus, job_id, {
                "type": "agent_status",
                "agent": "static_analyzer",
                "status": "completed",
                "progress": 100,
            })

            community_result = await _handle_community(
                results[2], job_id, cloned_path, self.timeout_guard, self.progress_bus
            )
            # Cache successful community results so future degradation paths
            # can read a real historical mean instead of hard-coded constants.
            if not community_result.is_degraded:
                try:
                    await self.timeout_guard.cache_community_result(
                        cloned_path, community_result
                    )
                except Exception:
                    pass
            await _publish(self.progress_bus, job_id, {
                "type": "agent_status",
                "agent": "community_assessor",
                "status": "completed" if not community_result.is_degraded else "degraded",
                "progress": 100,
            })

            if isinstance(results[1], BaseException):
                await _publish(self.progress_bus, job_id, {
                    "type": "degraded",
                    "agent": "behavior_inferer",
                    "reason": f"failed: {type(results[1]).__name__}",
                })
                partial = PartialReporterInput(
                    job_id=job_id,
                    static_result=static_result,
                    community_result=community_result,
                )
                return await self.emergency_reporter.render(partial, "behavior_inferer_failed")

            behavior_raw = results[1]
            await _publish(self.progress_bus, job_id, {
                "type": "agent_status",
                "agent": "behavior_inferer",
                "status": "completed",
                "progress": 100,
            })

            await _publish(self.progress_bus, job_id, {"type": "stage", "stage": "analysis", "status": "completed"})
            await _publish(self.progress_bus, job_id, {"type": "stage", "stage": "guardrail", "status": "running"})

            readme_text = await _load_readme(cloned_path)
            cleaned_behavior_text, guardrail_telemetry = await self.guardrail.validate(
                behavior_raw.to_text() if hasattr(behavior_raw, "to_text") else str(behavior_raw.core_modules),
                readme_text,
            )
            # BUG-V4-001 fix: fold BehaviorInferer input sanitizer counters into telemetry
            guardrail_telemetry.input_secrets_redacted = getattr(
                self.behavior_inferer, "last_input_secrets_redacted", 0
            )
            guardrail_telemetry.input_injections_blocked = getattr(
                self.behavior_inferer, "last_input_injections_blocked", 0
            )
            behavior_result = behavior_raw

            await _publish(self.progress_bus, job_id, {"type": "stage", "stage": "guardrail", "status": "completed"})

            elapsed = time.monotonic() - t_start
            if elapsed >= BUDGET_TOTAL_S - 2:
                raise BudgetExhaustedError(
                    f"Pipeline budget exhausted after {elapsed:.1f}s"
                )

            reporter_budget = min(BUDGET_REPORTER_S, BUDGET_TOTAL_S - elapsed - 2)

            await _publish(self.progress_bus, job_id, {"type": "stage", "stage": "reporter", "status": "running"})
            await _publish(self.progress_bus, job_id, {
                "type": "agent_status",
                "agent": "reporter",
                "status": "running",
                "progress": 15,
                "stage_label": "聚合三 Agent 结果...",
            })
            reporter_ticker = asyncio.create_task(
                _agent_progress_ticker(
                    self.progress_bus, job_id, "reporter", max(reporter_budget, 1.0)
                )
            )

            ctx = ReporterInput(
                job_id=job_id,
                repo_path=cloned_path,
                static_result=static_result,
                behavior_result=behavior_result,
                community_result=community_result,
                guardrail_telemetry=guardrail_telemetry,
                timeout_seconds=max(1, int(reporter_budget)),
                agent_durations={
                    "static_analyzer": static_result.duration_ms,
                    "behavior_inferer": behavior_result.duration_ms,
                    "community_assessor": community_result.duration_ms,
                },
                force_refresh=force_refresh,
            )

            reporter_start = time.monotonic()
            try:
                report = await asyncio.wait_for(
                    self.reporter.render(ctx), timeout=reporter_budget
                )
            except asyncio.TimeoutError:
                await _publish(self.progress_bus, job_id, {
                    "type": "degraded",
                    "agent": "reporter",
                    "reason": "reporter_timeout",
                })
                partial = PartialReporterInput(
                    job_id=job_id,
                    static_result=static_result,
                    behavior_result=behavior_result,
                    community_result=community_result,
                    guardrail_telemetry=guardrail_telemetry,
                )
                return await self.emergency_reporter.render(partial, "reporter_timeout")
            except Exception:
                await _publish(self.progress_bus, job_id, {
                    "type": "degraded",
                    "agent": "reporter",
                    "reason": "reporter_failed",
                })
                partial = PartialReporterInput(
                    job_id=job_id,
                    static_result=static_result,
                    behavior_result=behavior_result,
                    community_result=community_result,
                    guardrail_telemetry=guardrail_telemetry,
                )
                return await self.emergency_reporter.render(partial, "reporter_failed")
            finally:
                reporter_ticker.cancel()
                try:
                    await reporter_ticker
                except asyncio.CancelledError:
                    pass  # expected cancellation
                except Exception:
                    logger.exception("reporter progress ticker crashed")

            reporter_duration_ms = int((time.monotonic() - reporter_start) * 1000)
            if report.agent_durations is not None:
                report.agent_durations["reporter"] = reporter_duration_ms

            await _publish(self.progress_bus, job_id, {
                "type": "agent_status",
                "agent": "reporter",
                "status": "completed",
                "progress": 100,
            })
            await _publish(self.progress_bus, job_id, {"type": "stage", "stage": "reporter", "status": "completed"})
            await _publish(self.progress_bus, job_id, {
                "type": "completed",
                "job_id": job_id,
                "total_pipeline_ms": report.total_pipeline_ms,
            })

            total_elapsed_ms = int((time.monotonic() - t_start) * 1000)
            if self.observability:
                self.observability.record_pipeline(
                    job_id=job_id,
                    duration_ms=total_elapsed_ms,
                    stage_durations={
                        "static_ms": static_result.duration_ms,
                        "behavior_ms": behavior_result.duration_ms,
                        "community_ms": community_result.duration_ms,
                    },
                    guardrail_telemetry=guardrail_telemetry,
                    recommendation_count=len(report.recommendations),
                )

            return report

        finally:
            if cloned_path and self.repo_cloner:
                await self.repo_cloner.cleanup(cloned_path, source)
