from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.emergency_reporter import EmergencyReporter
from app.models.agent_schemas import (
    BehaviorResult,
    CommunityResult,
    FunctionRisk,
    RiskLevel,
    StaticResult,
)
from app.models.api_schemas import (
    GuardrailTelemetry,
    PartialReporterInput,
)
from app.orchestrator.planner import Planner


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_static(high_cc_file="utils.py") -> StaticResult:
    return StaticResult(
        job_id="job1",
        high_complexity_functions=[
            FunctionRisk(
                file=high_cc_file,
                line=5,
                name="complex_fn",
                cc=18,
                risk_level=RiskLevel.HIGH,
                suggestion="Split into smaller functions.",
            )
        ],
        low_coverage_modules=[],
        file_heatmap={},
        pylint_scores={},
        total_files_scanned=2,
        duration_ms=80,
    )


def _make_community(degraded=False) -> CommunityResult:
    return CommunityResult(
        job_id="job1",
        commits_per_week=4.0,
        unique_contributors=3,
        is_degraded=degraded,
        degraded_reason="cache fallback" if degraded else None,
        duration_ms=10,
    )


def _make_behavior() -> BehaviorResult:
    return BehaviorResult(
        job_id="job1",
        usage_patterns=["Process data"],
        core_modules=["utils"],
        inference_evidence={},
        guardrail_passed=True,
        duration_ms=30,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_emergency_report_on_reporter_timeout():
    er = EmergencyReporter()
    partial = PartialReporterInput(
        job_id="job1",
        static_result=_make_static(),
        community_result=_make_community(),
    )
    result = await er.render(partial, "reporter_timeout")
    assert result.job_id == "job1"
    assert result.guardrail_telemetry is not None
    assert result.guardrail_telemetry.emergency_mode is True
    assert result.guardrail_telemetry.emergency_reason == "reporter_timeout"


@pytest.mark.asyncio
async def test_emergency_report_preserves_partial_community():
    er = EmergencyReporter()
    community = _make_community(degraded=True)
    partial = PartialReporterInput(
        job_id="job1",
        static_result=_make_static(),
        community_result=community,
    )
    result = await er.render(partial, "behavior_inferer_failed")
    assert result.community is not None
    assert result.community.is_degraded is True
    assert result.community.degraded_reason == "cache fallback"


@pytest.mark.asyncio
async def test_emergency_report_html_banner():
    er = EmergencyReporter()
    partial = PartialReporterInput(job_id="job1")
    result = await er.render(partial, "reporter_timeout")
    assert result.html_report is not None
    assert "emergency-banner" in result.html_report
    assert "reporter_timeout" in result.html_report


@pytest.mark.asyncio
async def test_emergency_mode_telemetry_fields():
    er = EmergencyReporter()
    telemetry = GuardrailTelemetry(fallback_triggered=True)
    partial = PartialReporterInput(
        job_id="job2",
        guardrail_telemetry=telemetry,
    )
    result = await er.render(partial, "planner_budget_exhausted")
    t = result.guardrail_telemetry
    assert t is not None
    assert t.emergency_mode is True
    assert t.emergency_reason == "planner_budget_exhausted"
    assert t.fallback_triggered is True


@pytest.mark.asyncio
async def test_emergency_report_builds_recommendations_from_static():
    er = EmergencyReporter()
    partial = PartialReporterInput(
        job_id="job1",
        static_result=_make_static(),
    )
    result = await er.render(partial, "behavior_inferer_failed")
    assert len(result.recommendations) > 0
    assert any("complex_fn" in r.title for r in result.recommendations)


@pytest.mark.asyncio
async def test_emergency_report_no_static_gives_empty_recommendations():
    er = EmergencyReporter()
    partial = PartialReporterInput(job_id="job1")
    result = await er.render(partial, "reporter_timeout")
    assert result.recommendations == []


@pytest.mark.asyncio
async def test_emergency_report_community_fallback_when_none():
    er = EmergencyReporter()
    partial = PartialReporterInput(job_id="job1", community_result=None)
    result = await er.render(partial, "reporter_timeout")
    assert result.community is not None
    assert result.community.is_degraded is True


# ---------------------------------------------------------------------------
# Planner integration: BehaviorInferer failure routes to emergency_reporter
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_planner_uses_emergency_on_behavior_failure():
    from app.agents.static_analyzer import StaticAnalyzer
    from app.agents.behavior_inferer import BehaviorInferer
    from app.agents.community_assessor import CommunityAssessor
    from app.agents.reporter import Reporter
    from app.services.repo_cloner import RepoCloner
    from app.orchestrator.timeout_guard import TimeoutGuard

    static_result = _make_static()
    community_result = _make_community()

    mock_static = AsyncMock(spec=StaticAnalyzer)
    mock_static.run.return_value = static_result

    mock_bi = AsyncMock(spec=BehaviorInferer)
    mock_bi.infer.side_effect = RuntimeError("LLM API down")

    mock_community = AsyncMock(spec=CommunityAssessor)
    mock_community.run.return_value = community_result

    mock_reporter = AsyncMock(spec=Reporter)
    mock_reporter.render.return_value = MagicMock()

    mock_cloner = AsyncMock(spec=RepoCloner)
    mock_cloner.clone.return_value = "/tmp/cloned"
    mock_cloner.cleanup.return_value = None

    mock_timeout_guard = AsyncMock(spec=TimeoutGuard)
    mock_timeout_guard.get_degraded_community.return_value = community_result

    mock_er = AsyncMock(spec=EmergencyReporter)
    from app.models.api_schemas import CommunityMetrics, ReportJsonResponse
    from datetime import datetime, timezone
    mock_er.render.return_value = ReportJsonResponse(
        job_id="job1",
        status="completed",
        completed_at=datetime.now(timezone.utc),
        total_pipeline_ms=50,
        recommendations=[],
        community=CommunityMetrics(commits_per_week=0.0, unique_contributors=0),
        guardrail_telemetry=GuardrailTelemetry(emergency_mode=True, emergency_reason="behavior_inferer_failed"),
    )

    planner = Planner(
        static_analyzer=mock_static,
        behavior_inferer=mock_bi,
        community_assessor=mock_community,
        reporter=mock_reporter,
        emergency_reporter=mock_er,
        repo_cloner=mock_cloner,
        timeout_guard=mock_timeout_guard,
    )

    result = await planner.run_pipeline("job1", "local", "/some/repo")

    mock_er.render.assert_called_once()
    call_args = mock_er.render.call_args
    assert call_args[0][1] == "behavior_inferer_failed"
    assert result.guardrail_telemetry is not None
    assert result.guardrail_telemetry.emergency_mode is True
