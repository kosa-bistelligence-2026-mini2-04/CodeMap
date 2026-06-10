from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.provider import BudgetExhaustedError
from app.models.agent_schemas import (
    BehaviorResult,
    CommunityResult,
    FunctionRisk,
    ReporterInput,
    RiskLevel,
    StaticResult,
)
from app.models.api_schemas import GuardrailTelemetry, ReportJsonResponse, CommunityMetrics
from app.orchestrator.conflict_resolver import ConflictResolver
from app.orchestrator.planner import BUDGET_TOTAL_S, Planner, _handle_community
from app.orchestrator.timeout_guard import TimeoutGuard


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_static_result(job_id="test-job", file="utils.py", cc=12) -> StaticResult:
    return StaticResult(
        job_id=job_id,
        high_complexity_functions=[
            FunctionRisk(
                file=file,
                line=10,
                name="do_thing",
                cc=cc,
                risk_level=RiskLevel.HIGH,
                suggestion="Refactor",
            )
        ],
        low_coverage_modules=[],
        file_heatmap={},
        pylint_scores={},
        total_files_scanned=1,
        duration_ms=100,
    )


def _make_behavior_result(job_id="test-job", core_modules=None) -> BehaviorResult:
    return BehaviorResult(
        job_id=job_id,
        usage_patterns=["pattern1"],
        core_modules=core_modules or ["utils"],
        inference_evidence={},
        guardrail_passed=True,
        duration_ms=200,
    )


def _make_community_result(job_id="test-job") -> CommunityResult:
    return CommunityResult(
        job_id=job_id,
        commits_per_week=5.0,
        unique_contributors=3,
        duration_ms=50,
    )


def _make_report_response(job_id="test-job") -> ReportJsonResponse:
    from datetime import datetime, timezone
    return ReportJsonResponse(
        job_id=job_id,
        status="completed",
        completed_at=datetime.now(timezone.utc),
        total_pipeline_ms=500,
        recommendations=[],
        community=CommunityMetrics(commits_per_week=5.0, unique_contributors=3),
        html_report="<html/>",
        guardrail_telemetry=None,
    )


# ---------------------------------------------------------------------------
# T4 Test 1: CancelledError propagates (not degraded)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_cancelled_error_propagates():
    """CancelledError from community assessor must be re-raised, not degraded."""
    timeout_guard = TimeoutGuard(db_path=":memory:")
    result = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await _handle_community(result, "job1", "/repo", timeout_guard)


# ---------------------------------------------------------------------------
# T4 Test 2: TimeoutError degrades community
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_timeout_error_degrades_community(tmp_path):
    timeout_guard = TimeoutGuard(db_path=str(tmp_path / "cache.db"))
    result = asyncio.TimeoutError()
    community = await _handle_community(result, "job2", "/repo", timeout_guard)
    assert community.is_degraded is True
    assert community.commits_per_week == 3.5


# ---------------------------------------------------------------------------
# T4 Test 3: Unknown exception degrades community
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unknown_exception_degrades(tmp_path):
    timeout_guard = TimeoutGuard(db_path=str(tmp_path / "cache.db"))
    result = RuntimeError("boom")
    community = await _handle_community(result, "job3", "/repo", timeout_guard)
    assert community.is_degraded is True


# ---------------------------------------------------------------------------
# T4 Test 4: Budget exhausted -> outer wrapper returns emergency (BUG-R8)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_budget_exhausted_returns_emergency():
    """BudgetExhaustedError inside _run_pipeline_inner is caught by run_pipeline -> emergency report."""
    static_result = _make_static_result()
    behavior_result = _make_behavior_result()
    community_result = _make_community_result()
    report_response = _make_report_response()

    mock_cloner = AsyncMock()
    mock_cloner.clone.return_value = "/tmp/repo"
    mock_cloner.cleanup.return_value = None

    mock_static = AsyncMock()
    mock_static.run.return_value = static_result

    mock_behavior = AsyncMock()
    mock_behavior.infer.return_value = behavior_result

    mock_community = AsyncMock()
    mock_community.run.return_value = community_result

    mock_reporter = AsyncMock()
    mock_reporter.render.return_value = report_response

    mock_guardrail = AsyncMock()
    mock_guardrail.validate.return_value = ("cleaned", GuardrailTelemetry())

    from datetime import datetime, timezone
    emergency_response = ReportJsonResponse(
        job_id="job4",
        status="completed",
        completed_at=datetime.now(timezone.utc),
        total_pipeline_ms=0,
        recommendations=[],
        community=CommunityMetrics(commits_per_week=0.0, unique_contributors=0),
        guardrail_telemetry=GuardrailTelemetry(
            emergency_mode=True, emergency_reason="planner_budget_exhausted"
        ),
    )
    mock_emergency = AsyncMock()
    mock_emergency.render = AsyncMock(return_value=emergency_response)

    planner = Planner(
        static_analyzer=mock_static,
        behavior_inferer=mock_behavior,
        community_assessor=mock_community,
        reporter=mock_reporter,
        repo_cloner=mock_cloner,
        guardrail=mock_guardrail,
        emergency_reporter=mock_emergency,
    )

    # Simulate budget exhausted by patching time.monotonic
    original_monotonic = time.monotonic
    start_ref = [None]

    def fake_monotonic():
        if start_ref[0] is None:
            start_ref[0] = original_monotonic()
            return start_ref[0]
        return start_ref[0] + BUDGET_TOTAL_S

    with patch("app.orchestrator.planner.time.monotonic", side_effect=fake_monotonic):
        result = await planner.run_pipeline("job4", "local", "/tmp/repo")

    assert result.guardrail_telemetry is not None
    assert result.guardrail_telemetry.emergency_mode is True


# ---------------------------------------------------------------------------
# T4 Test 5: gather concurrency (3 agents run in parallel)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gather_concurrency():
    """3 agents simulated with delays: wall-clock should be < max(delays) * 1.5."""
    static_result = _make_static_result()
    behavior_result = _make_behavior_result()
    community_result = _make_community_result()
    report_response = _make_report_response()

    async def slow_static(inp):
        await asyncio.sleep(0.05)
        return static_result

    async def slow_behavior(inp):
        await asyncio.sleep(0.1)
        return behavior_result

    async def slow_community(inp):
        await asyncio.sleep(0.08)
        return community_result

    mock_static = MagicMock()
    mock_static.run = slow_static

    mock_behavior = MagicMock()
    mock_behavior.infer = slow_behavior

    mock_community = MagicMock()
    mock_community.run = slow_community

    mock_cloner = AsyncMock()
    mock_cloner.clone.return_value = "/tmp/repo"
    mock_cloner.cleanup.return_value = None

    mock_reporter = AsyncMock()
    mock_reporter.render.return_value = report_response

    mock_guardrail = AsyncMock()
    mock_guardrail.validate.return_value = ("cleaned", GuardrailTelemetry())

    planner = Planner(
        static_analyzer=mock_static,
        behavior_inferer=mock_behavior,
        community_assessor=mock_community,
        reporter=mock_reporter,
        repo_cloner=mock_cloner,
        guardrail=mock_guardrail,
    )

    t0 = time.monotonic()
    result = await planner.run_pipeline("job5", "local", "/tmp/repo")
    elapsed = time.monotonic() - t0

    # Max individual time is 0.1s; sequential sum is 0.23s.
    # With gather, wall-clock should be close to 0.1s (max), not 0.23s (sum).
    assert elapsed < 0.23, f"Expected < 0.23s (parallel), got {elapsed:.3f}s"
    assert result.job_id == "test-job"


# ---------------------------------------------------------------------------
# T4 Test 6: ConflictResolver module overlap
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_conflict_resolver_module_overlap():
    """static marks utils.py high + behavior marks utils as core -> resolve produces recommendation."""
    static = _make_static_result(file="utils.py", cc=15)
    behavior = _make_behavior_result(core_modules=["utils"])

    resolver = ConflictResolver(llm_provider=None)
    resolutions = await resolver.resolve(static, behavior)

    assert len(resolutions) == 1
    assert resolutions[0].module == "utils"
    assert "utils" in resolutions[0].final_recommendation.lower() or len(resolutions[0].final_recommendation) > 10


# ---------------------------------------------------------------------------
# T4 Test 7: JudgeGuardrail skips future-tense, keeps absolute
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_judge_guardrail_skips_future_tense():
    """JudgeGuardrail should NOT block future-tense text but SHOULD block absolute language."""
    from app.guardrail.judge_guardrail import JudgeGuardrail

    guardrail = JudgeGuardrail()

    text_with_future = "This module will be refactored in 2027 and improved."
    text_with_absolute = "This must always be refactored, 100% guaranteed."

    # Future tense should pass through (not blocked)
    cleaned_future, telemetry_future = await guardrail.validate(text_with_future, "source context")
    future_rule_ids = [b.rule_id for b in telemetry_future.regex_blocked]
    assert "future_tense" not in future_rule_ids, "JudgeGuardrail must skip FUTURE_TENSE"

    # Absolute language should be blocked
    cleaned_absolute, telemetry_absolute = await guardrail.validate(text_with_absolute, "source context")
    absolute_rule_ids = [b.rule_id for b in telemetry_absolute.regex_blocked]
    assert "absolute" in absolute_rule_ids, "JudgeGuardrail must catch ABSOLUTE overconfidence"


# ---------------------------------------------------------------------------
# T5 Test: Planner top-level budget exhausted -> emergency report (BUG-R8)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_planner_total_budget_exhausted_emergency():
    """When _run_pipeline_inner exceeds BUDGET_TOTAL_S, run_pipeline returns emergency mode."""
    mock_emergency = AsyncMock()
    from datetime import datetime, timezone
    emergency_response = ReportJsonResponse(
        job_id="job-r8",
        status="completed",
        completed_at=datetime.now(timezone.utc),
        total_pipeline_ms=0,
        recommendations=[],
        community=CommunityMetrics(commits_per_week=0.0, unique_contributors=0),
        guardrail_telemetry=GuardrailTelemetry(emergency_mode=True, emergency_reason="planner_budget_exhausted"),
    )
    mock_emergency.render = AsyncMock(return_value=emergency_response)

    planner = Planner(emergency_reporter=mock_emergency)

    async def _hang(job_id, source, path, force_refresh=False, model_override=None):
        await asyncio.sleep(9999)

    with patch.object(planner, "_run_pipeline_inner", side_effect=_hang):
        with patch("app.orchestrator.planner.BUDGET_TOTAL_S", 0.05):
            result = await planner.run_pipeline("job-r8", "local", "/tmp/repo")

    assert result.guardrail_telemetry is not None
    assert result.guardrail_telemetry.emergency_mode is True
    assert result.guardrail_telemetry.emergency_reason == "planner_budget_exhausted"
    mock_emergency.render.assert_awaited_once()
    _, called_reason = mock_emergency.render.await_args.args
    assert called_reason == "planner_budget_exhausted"


# ---------------------------------------------------------------------------
# BUG-NEW-2 Tests: inner vs outer timeout distinction
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_inner_agent_timeout_not_reported_as_planner_budget():
    """Inner agent TimeoutError (consumed inside _run_pipeline_inner) does NOT trigger planner_budget_exhausted."""
    mock_emergency = AsyncMock()
    from datetime import datetime, timezone

    emergency_response = ReportJsonResponse(
        job_id="job-inner",
        status="completed",
        completed_at=datetime.now(timezone.utc),
        total_pipeline_ms=0,
        recommendations=[],
        community=CommunityMetrics(commits_per_week=0.0, unique_contributors=0),
        guardrail_telemetry=GuardrailTelemetry(emergency_mode=True, emergency_reason="behavior_inferer_failed"),
    )
    mock_emergency.render = AsyncMock(return_value=emergency_response)

    static_result = _make_static_result()
    community_result = _make_community_result()

    mock_cloner = AsyncMock()
    mock_cloner.clone.return_value = "/tmp/repo"
    mock_cloner.cleanup.return_value = None

    mock_static = AsyncMock()
    mock_static.run.return_value = static_result

    # behavior_inferer raises TimeoutError — simulating an inner agent timeout
    mock_behavior = AsyncMock()
    mock_behavior.infer.side_effect = asyncio.TimeoutError()

    mock_community = AsyncMock()
    mock_community.run.return_value = community_result

    mock_guardrail = AsyncMock()
    mock_guardrail.validate.return_value = ("cleaned", GuardrailTelemetry())

    planner = Planner(
        static_analyzer=mock_static,
        behavior_inferer=mock_behavior,
        community_assessor=mock_community,
        repo_cloner=mock_cloner,
        guardrail=mock_guardrail,
        emergency_reporter=mock_emergency,
    )

    result = await planner.run_pipeline("job-inner", "local", "/tmp/repo")

    # Inner behavior_inferer timeout is handled as behavior_inferer_failed, not planner_budget_exhausted
    assert result.guardrail_telemetry is not None
    called_reason = mock_emergency.render.await_args.args[1]
    assert called_reason != "planner_budget_exhausted", (
        f"Inner agent timeout must not bubble up as planner_budget_exhausted, got: {called_reason}"
    )


@pytest.mark.asyncio
async def test_outer_total_timeout_is_planner_budget():
    """When the outer BUDGET_TOTAL_S wait_for fires, emergency_reason is planner_budget_exhausted."""
    mock_emergency = AsyncMock()
    from datetime import datetime, timezone

    emergency_response = ReportJsonResponse(
        job_id="job-outer",
        status="completed",
        completed_at=datetime.now(timezone.utc),
        total_pipeline_ms=0,
        recommendations=[],
        community=CommunityMetrics(commits_per_week=0.0, unique_contributors=0),
        guardrail_telemetry=GuardrailTelemetry(emergency_mode=True, emergency_reason="planner_budget_exhausted"),
    )
    mock_emergency.render = AsyncMock(return_value=emergency_response)

    planner = Planner(emergency_reporter=mock_emergency)

    async def _infinite_inner(job_id, source, path, force_refresh=False, model_override=None):
        await asyncio.sleep(9999)

    with patch.object(planner, "_run_pipeline_inner", side_effect=_infinite_inner):
        with patch("app.orchestrator.planner.BUDGET_TOTAL_S", 0.05):
            result = await planner.run_pipeline("job-outer", "local", "/tmp/repo")

    assert result.guardrail_telemetry is not None
    called_reason = mock_emergency.render.await_args.args[1]
    assert called_reason == "planner_budget_exhausted"


# ---------------------------------------------------------------------------
# BUG-NEW-2 Additional: static_analyzer inner timeout -> static_analyzer_failed
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_static_analyzer_timeout_not_reported_as_planner_budget():
    """StaticAnalyzer TimeoutError must go to static_analyzer_failed, not planner_budget_exhausted."""
    from datetime import datetime, timezone

    emergency_response = ReportJsonResponse(
        job_id="job-static-timeout",
        status="completed",
        completed_at=datetime.now(timezone.utc),
        total_pipeline_ms=0,
        recommendations=[],
        community=CommunityMetrics(commits_per_week=0.0, unique_contributors=0),
        guardrail_telemetry=GuardrailTelemetry(emergency_mode=True, emergency_reason="static_analyzer_failed"),
    )
    mock_emergency = AsyncMock()
    mock_emergency.render = AsyncMock(return_value=emergency_response)

    community_result = _make_community_result()

    mock_cloner = AsyncMock()
    mock_cloner.clone.return_value = "/tmp/repo"
    mock_cloner.cleanup.return_value = None

    mock_static = AsyncMock()
    mock_static.run.side_effect = asyncio.TimeoutError()

    mock_behavior = AsyncMock()
    mock_behavior.infer.return_value = _make_behavior_result()

    mock_community = AsyncMock()
    mock_community.run.return_value = community_result

    mock_guardrail = AsyncMock()
    mock_guardrail.validate.return_value = ("cleaned", GuardrailTelemetry())

    planner = Planner(
        static_analyzer=mock_static,
        behavior_inferer=mock_behavior,
        community_assessor=mock_community,
        repo_cloner=mock_cloner,
        guardrail=mock_guardrail,
        emergency_reporter=mock_emergency,
    )

    result = await planner.run_pipeline("job-static-timeout", "local", "/tmp/repo")

    assert result.guardrail_telemetry is not None
    called_reason = mock_emergency.render.await_args.args[1]
    assert called_reason == "static_analyzer_failed", (
        f"StaticAnalyzer timeout must not bubble up as planner_budget_exhausted, got: {called_reason}"
    )
