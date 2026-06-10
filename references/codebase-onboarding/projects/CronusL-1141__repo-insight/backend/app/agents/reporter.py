from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

from app.agents.base import BaseAgent
from app.models.agent_schemas import (
    BehaviorResult,
    CommunityResult,
    Recommendation,
    ReporterInput,
    ReportResult,
    RiskLevel,
    StaticResult,
)
from app.models.api_schemas import CommunityMetrics, GuardrailTelemetry, LineRiskHttp, ReportJsonResponse, PartialReporterInput

if TYPE_CHECKING:
    from app.orchestrator.conflict_resolver import ConflictResolver

_RISK_ORDER = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
_RISK_VALUE = {r: i for i, r in enumerate(_RISK_ORDER)}

_RISK_NUMERIC = {
    RiskLevel.LOW: 1,
    RiskLevel.MEDIUM: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}


def _build_echarts_heatmap_config(file_heatmap: dict[str, list[LineRiskHttp]]) -> str:
    """Build ECharts heatmap series config as JSON string."""
    files = sorted(file_heatmap.keys())
    data = []
    for x_idx, file_path in enumerate(files):
        for lr in file_heatmap[file_path]:
            data.append([x_idx, lr.line, _RISK_NUMERIC.get(lr.risk_level, 1)])

    config = {
        "title": {"text": "Code Risk Heatmap"},
        "tooltip": {"position": "top"},
        "grid": {"height": "50%", "top": "10%"},
        "xAxis": {
            "type": "category",
            "data": files,
            "splitArea": {"show": True},
            "axisLabel": {"rotate": 45, "fontSize": 10},
        },
        "yAxis": {
            "type": "value",
            "name": "Line",
        },
        "visualMap": {
            "min": 1,
            "max": 4,
            "calculable": True,
            "orient": "horizontal",
            "left": "center",
            "bottom": "15%",
            "inRange": {"color": ["#50a3ba", "#eac736", "#d94e5d"]},
        },
        "series": [
            {
                "name": "Risk",
                "type": "heatmap",
                "data": data,
                "label": {"show": False},
                "emphasis": {"itemStyle": {"shadowBlur": 10}},
            }
        ],
    }
    return json.dumps(config, ensure_ascii=False)


def _build_recommendations(
    static: StaticResult,
    behavior: BehaviorResult,
) -> list[Recommendation]:
    """Generate Top-3 recommendations; upgrade priority if module in core_modules."""
    behavior_module_normalized = {
        m.replace("\\", "/").split("/")[0].replace(".py", "")
        for m in behavior.core_modules
    }

    sorted_funcs = sorted(
        static.high_complexity_functions,
        key=lambda f: f.cc,
        reverse=True,
    )

    recs: list[Recommendation] = []
    seen_titles: set[str] = set()
    for func in sorted_funcs[:3]:
        func_module = func.file.replace("\\", "/").split("/")[0].replace(".py", "")
        priority = RiskLevel.HIGH if func.risk_level.value in ("high", "critical") else func.risk_level

        if func_module in behavior_module_normalized:
            priority = RiskLevel.CRITICAL

        title = f"重构 {func.file} 中的 {func.name}（圈复杂度 CC={func.cc}）"
        if title in seen_titles:
            continue
        seen_titles.add(title)
        recs.append(
            Recommendation(
                title=title,
                detail=func.suggestion,
                affected_files=[func.file],
                priority=priority,
            )
        )

    fallback_title = "补充单元测试以提升覆盖率"
    if len(recs) < 3 and fallback_title not in seen_titles:
        recs.append(
            Recommendation(
                title=fallback_title,
                detail=(
                    "为覆盖率较低的模块补充单元测试，建议目标行覆盖率不低于 70%，"
                    "优先覆盖核心业务逻辑与边界分支。"
                ),
                affected_files=[m.path for m in static.low_coverage_modules[:3]],
                priority=RiskLevel.MEDIUM,
            )
        )

    return recs[:3]


def _build_html_report(
    job_id: str,
    static: StaticResult,
    behavior: BehaviorResult,
    community: CommunityMetrics,
    recommendations: list[Recommendation],
    conflicts: list,
    guardrail_telemetry: GuardrailTelemetry | None,
    echarts_config: str,
    total_pipeline_ms: int,
) -> str:
    community_degraded_html = (
        f'<p class="warn">社区数据暂不可用，采用历史均值估算 (commits_per_week ≈ {community.commits_per_week})</p>'
        if community.is_degraded
        else ""
    )

    recs_html = "".join(
        f'<li><strong>[{r.priority.value.upper()}]</strong> {r.title}<br><em>{r.detail}</em></li>'
        for r in recommendations
    )

    conflicts_html = ""
    if conflicts:
        items = "".join(
            f"<li><strong>{c.module}</strong>: {c.final_recommendation}</li>"
            for c in conflicts
        )
        conflicts_html = f"<h3>Conflicts Resolved</h3><ul>{items}</ul>"

    guardrail_badge = ""
    if guardrail_telemetry and guardrail_telemetry.fallback_triggered:
        guardrail_badge = '<span class="badge warn">AI Output: Fallback Triggered</span>'
    elif guardrail_telemetry and (guardrail_telemetry.regex_blocked or guardrail_telemetry.semantic_filtered):
        n = len(guardrail_telemetry.regex_blocked) + len(guardrail_telemetry.semantic_filtered)
        guardrail_badge = f'<span class="badge info">AI Output: {n} item(s) filtered by guardrail</span>'

    return f"""<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<title>RepoInsight Report — {job_id}</title>
<style>
body{{font-family:sans-serif;max-width:900px;margin:0 auto;padding:1rem}}
.card{{background:#f8f9fa;border-radius:8px;padding:1rem;margin-bottom:1rem}}
.badge{{display:inline-block;padding:.2rem .6rem;border-radius:4px;font-size:.8rem}}
.badge.warn{{background:#fff3cd;color:#856404}}
.badge.info{{background:#d1ecf1;color:#0c5460}}
.warn{{color:#856404;background:#fff3cd;padding:.4rem;border-radius:4px}}
ul{{padding-left:1.2rem}}
</style>
</head>
<body>
<h1>RepoInsight Analysis Report</h1>
<div class="card">
  <h2>Summary</h2>
  <p>Job ID: <code>{job_id}</code></p>
  <p>Total pipeline: <strong>{total_pipeline_ms}ms</strong></p>
  <p>Status: <strong>completed</strong></p>
  {guardrail_badge}
</div>
<div class="card">
  <h2>Top Recommendations</h2>
  <ol>{recs_html}</ol>
</div>
<div class="card">
  <h2>Risk Heatmap</h2>
  <div data-echarts-config='{echarts_config}' style="height:400px;width:100%"></div>
</div>
<div class="card">
  <h2>Community Health</h2>
  {community_degraded_html}
  <ul>
    <li>Commits/week: {community.commits_per_week:.1f}</li>
    <li>Unique contributors: {community.unique_contributors}</li>
    <li>Avg issue response: {community.avg_issue_response_hours or 'N/A'}</li>
  </ul>
</div>
{f'<div class="card">{conflicts_html}</div>' if conflicts_html else ''}
</body>
</html>"""


_EXECUTIVE_SUMMARY_PROMPT = """你是 RepoInsight 报告摘要 Agent。根据提供的分析结果，用中文生成一份结构化的执行摘要。

## 输入数据
- 代码规模：{total_files} 个 Python 文件
- 高复杂度函数 Top3：{top_funcs}
- 推断的使用场景：{usage_patterns}
- 推断的核心模块：{core_modules}
- 社区活跃度：每周 {commits_per_week} 次提交，{contributors} 位贡献者
- 已识别的冲突数：{conflict_count}

## 输出要求 JSON（必须合法，禁止 markdown 代码块包裹）
{{
  "summary": "150 字以内的中文自然语言摘要，覆盖代码质量/使用场景/社区健康三方面",
  "health_score": 0-100 的整数，基于代码质量 + 社区活跃度综合打分,
  "key_strengths": ["优势 1", "优势 2"] — 最多 3 条，每条 ≤ 30 字,
  "key_risks": ["风险 1", "风险 2"] — 最多 3 条，每条 ≤ 30 字,
  "confidence": 0.0-1.0 的浮点数，反映你对该摘要准确性的信心
}}

## 约束
- summary 客观中性，禁止编造数据外的内容
- summary 不要 markdown 格式或 "以下是" 类元语言
- 所有字段必须存在（即使 key_strengths/key_risks 为空数组）
- health_score 必须基于输入数据，不能随意给分

只输出 JSON 本身，不要任何前缀后缀。
"""


class Reporter(BaseAgent):
    """Aggregates results from all agents and generates the final JSON report."""

    name = "reporter"

    def __init__(
        self,
        conflict_resolver: "ConflictResolver | None" = None,
        llm_provider=None,
        cache=None,
        guardrail=None,
    ) -> None:
        self.conflict_resolver = conflict_resolver
        self.llm_provider = llm_provider
        self.cache = cache
        self.guardrail = guardrail

    async def run(self, input_data: ReporterInput) -> ReportResult:
        raise NotImplementedError("Use Reporter.render() directly")

    async def _generate_executive_summary(
        self,
        static: StaticResult,
        behavior: BehaviorResult,
        community: CommunityResult,
        conflict_count: int,
        force_refresh: bool = False,
    ) -> dict | None:
        """Call LLM to generate a structured JSON executive summary.

        Returns dict with keys {summary, health_score, key_strengths, key_risks,
        confidence}, or None on any failure. Best-effort — never blocks the report.
        """
        if self.llm_provider is None:
            return None

        top_funcs = ", ".join(
            f"{f.name}(CC={f.cc})" for f in static.high_complexity_functions[:3]
        ) or "无"
        usage = "; ".join(behavior.usage_patterns[:3]) or "未推断出"
        modules = ", ".join(behavior.core_modules[:5]) or "未推断出"

        prompt = _EXECUTIVE_SUMMARY_PROMPT.format(
            total_files=static.total_files_scanned,
            top_funcs=top_funcs,
            usage_patterns=usage[:500],
            core_modules=modules[:500],
            commits_per_week=f"{community.commits_per_week:.1f}",
            contributors=community.unique_contributors,
            conflict_count=conflict_count,
        )

        # Try cache first if we have one
        cache_key_str: str | None = None
        if self.cache is not None and not force_refresh:
            import hashlib
            cache_key_str = "reporter_summary::v2::" + hashlib.sha256(
                prompt.encode("utf-8")
            ).hexdigest()[:32]
            try:
                cached = await self.cache.get(cache_key_str)
                if cached:
                    parsed = self._parse_summary_json(cached)
                    if parsed is not None:
                        return parsed
            except Exception as exc:
                logger.debug("executive summary cache get failed: %s", exc)

        try:
            raw = await asyncio.wait_for(
                self.llm_provider.complete(
                    prompt=prompt,
                    response_format={"type": "json_object"},
                    temperature=0.2,
                ),
                timeout=15.0,
            )
        except Exception as exc:
            logger.warning(
                "executive summary LLM call failed (best-effort, summary omitted): %s: %s",
                exc.__class__.__name__, exc,
            )
            return None

        if not raw:
            return None

        parsed = self._parse_summary_json(raw)
        if parsed is None:
            return None

        # Best-effort guardrail on the freetext summary field only
        if self.guardrail is not None and parsed.get("summary"):
            try:
                cleaned, _tel = await self.guardrail.validate(parsed["summary"], "")
                if cleaned:
                    parsed["summary"] = cleaned.strip()[:400]
            except Exception as exc:
                logger.debug("summary guardrail pass-through failed: %s", exc)

        if self.cache is not None and cache_key_str is not None:
            try:
                await self.cache.set(cache_key_str, raw)
            except Exception as exc:
                logger.debug("executive summary cache set failed: %s", exc)

        return parsed

    @staticmethod
    def _parse_summary_json(raw: str) -> dict | None:
        """Parse + normalize the LLM JSON executive summary. Returns None on failure."""
        try:
            payload = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
        if not isinstance(payload, dict):
            return None

        summary = str(payload.get("summary", "")).strip()[:400]
        if not summary:
            return None

        def _as_str_list(v: object, max_items: int, max_len: int) -> list[str]:
            if not isinstance(v, list):
                return []
            out: list[str] = []
            for item in v[:max_items]:
                if isinstance(item, str):
                    s = item.strip()
                    if s:
                        out.append(s[:max_len])
            return out

        health_raw = payload.get("health_score")
        try:
            health_score = int(health_raw) if health_raw is not None else None
            if health_score is not None:
                health_score = max(0, min(100, health_score))
        except (TypeError, ValueError):
            health_score = None

        conf_raw = payload.get("confidence")
        try:
            confidence = float(conf_raw) if conf_raw is not None else None
            if confidence is not None:
                confidence = max(0.0, min(1.0, confidence))
        except (TypeError, ValueError):
            confidence = None

        return {
            "summary": summary,
            "health_score": health_score,
            "key_strengths": _as_str_list(payload.get("key_strengths"), 3, 60),
            "key_risks": _as_str_list(payload.get("key_risks"), 3, 60),
            "confidence": confidence,
        }

    def _self_check(self, draft: ReportJsonResponse, ctx: ReporterInput) -> list[str]:
        warnings = []
        if draft.total_pipeline_ms <= 0:
            warnings.append("total_pipeline_ms 非正数")
        if not draft.recommendations and ctx.static_result.high_complexity_functions:
            warnings.append("有高复杂度函数但 recommendations 为空")
        if draft.file_heatmap is None and ctx.static_result.high_complexity_functions:
            warnings.append("有高复杂度函数但 file_heatmap 缺失")
        static_files = {f.file for f in ctx.static_result.high_complexity_functions}
        behavior_modules = set(ctx.behavior_result.core_modules)
        for conflict in draft.conflicts_resolved:
            if conflict.module not in static_files and conflict.module not in behavior_modules:
                warnings.append(f"conflict 引用了不存在的 module: {conflict.module}")
        if ctx.community_result.is_degraded and not (draft.community and draft.community.is_degraded):
            warnings.append("community 降级未正确透传到报告")
        return warnings

    async def render(self, ctx: ReporterInput) -> ReportJsonResponse:
        """Aggregate StaticResult / BehaviorResult / CommunityResult into ReportJsonResponse."""
        t_start = time.monotonic()

        static: StaticResult = ctx.static_result
        behavior: BehaviorResult = ctx.behavior_result
        community: CommunityResult = ctx.community_result

        file_heatmap: dict[str, list[LineRiskHttp]] = {
            file_path: [
                LineRiskHttp(line=lr.line, risk_level=lr.risk_level, reason=lr.reason)
                for lr in line_risks
            ]
            for file_path, line_risks in static.file_heatmap.items()
        }

        community_metrics = CommunityMetrics(
            commits_per_week=community.commits_per_week,
            avg_issue_response_hours=community.avg_issue_response_hours,
            unique_contributors=community.unique_contributors,
            top_contributors=community.top_contributors,
            is_degraded=community.is_degraded,
            degraded_reason=community.degraded_reason,
            llm_analysis=getattr(community, "llm_analysis", None),
        )

        recommendations = _build_recommendations(static, behavior)

        conflicts_resolved = []
        if self.conflict_resolver is not None:
            try:
                conflicts_resolved = await self.conflict_resolver.resolve(static, behavior)
            except Exception:
                logger.exception(
                    "conflict resolver failed, proceeding without conflict resolution"
                )
                conflicts_resolved = []

        # LLM-generated executive summary (best-effort, never blocks the report)
        force_refresh = bool(getattr(ctx, "force_refresh", False))
        summary_payload = await self._generate_executive_summary(
            static, behavior, community, len(conflicts_resolved), force_refresh,
        )
        if summary_payload is not None:
            executive_summary = summary_payload.get("summary")
            health_score = summary_payload.get("health_score")
            key_strengths = summary_payload.get("key_strengths") or []
            key_risks = summary_payload.get("key_risks") or []
            summary_confidence = summary_payload.get("confidence")
        else:
            executive_summary = None
            health_score = None
            key_strengths = []
            key_risks = []
            summary_confidence = None

        guardrail_telemetry: GuardrailTelemetry | None = getattr(ctx, "guardrail_telemetry", None)

        echarts_config = _build_echarts_heatmap_config(file_heatmap)

        total_pipeline_ms = static.duration_ms + behavior.duration_ms + community.duration_ms
        render_ms = int((time.monotonic() - t_start) * 1000)

        html_report = _build_html_report(
            job_id=ctx.job_id,
            static=static,
            behavior=behavior,
            community=community_metrics,
            recommendations=recommendations,
            conflicts=conflicts_resolved,
            guardrail_telemetry=guardrail_telemetry,
            echarts_config=echarts_config,
            total_pipeline_ms=total_pipeline_ms + render_ms,
        )

        agent_durations: dict[str, int] = getattr(ctx, "agent_durations", {}) or {}

        draft = ReportJsonResponse(
            job_id=ctx.job_id,
            status="completed",
            completed_at=datetime.now(timezone.utc),
            total_pipeline_ms=total_pipeline_ms + render_ms,
            recommendations=recommendations,
            conflicts_resolved=conflicts_resolved,
            community=community_metrics,
            html_report=html_report,
            file_heatmap=file_heatmap if file_heatmap else None,
            guardrail_telemetry=guardrail_telemetry,
            agent_durations=agent_durations,
            executive_summary=executive_summary,
            health_score=health_score,
            key_strengths=key_strengths,
            key_risks=key_risks,
            summary_confidence=summary_confidence,
        )

        sc_warnings = self._self_check(draft, ctx)
        if sc_warnings:
            if draft.guardrail_telemetry is None:
                draft.guardrail_telemetry = GuardrailTelemetry()
            draft.guardrail_telemetry.self_check_warnings = sc_warnings

        return draft
