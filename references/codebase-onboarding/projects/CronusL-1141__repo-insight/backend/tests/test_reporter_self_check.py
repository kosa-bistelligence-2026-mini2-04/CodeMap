from __future__ import annotations

import pytest

from app.agents.reporter import Reporter
from app.models.agent_schemas import (
    BehaviorResult,
    CommunityResult,
    FunctionRisk,
    ReporterInput,
    RiskLevel,
    StaticResult,
    ConflictResolution,
)
from app.models.api_schemas import (
    CommunityMetrics,
    GuardrailTelemetry,
    ReportJsonResponse,
)
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_static(high_cc_file="utils.py", cc=15, include_heatmap=True) -> StaticResult:
    return StaticResult(
        job_id="test",
        high_complexity_functions=[
            FunctionRisk(
                file=high_cc_file,
                line=10,
                name="do_thing",
                cc=cc,
                risk_level=RiskLevel.HIGH,
                suggestion="Refactor.",
            )
        ],
        low_coverage_modules=[],
        file_heatmap={high_cc_file: []} if include_heatmap else {},
        pylint_scores={},
        total_files_scanned=1,
        duration_ms=100,
    )


def _make_behavior(core_modules=None) -> BehaviorResult:
    return BehaviorResult(
        job_id="test",
        usage_patterns=[],
        core_modules=core_modules or [],
        inference_evidence={},
        guardrail_passed=True,
        duration_ms=50,
    )


def _make_community(is_degraded=False) -> CommunityResult:
    return CommunityResult(
        job_id="test",
        commits_per_week=3.0,
        unique_contributors=2,
        is_degraded=is_degraded,
        degraded_reason="timeout" if is_degraded else None,
        duration_ms=20,
    )


def _make_ctx(static=None, behavior=None, community=None) -> ReporterInput:
    return ReporterInput(
        job_id="test",
        repo_path="/tmp/repo",
        static_result=static or _make_static(),
        behavior_result=behavior or _make_behavior(),
        community_result=community or _make_community(),
    )


def _make_draft(
    recommendations=None,
    file_heatmap=None,
    conflicts_resolved=None,
    community_is_degraded=False,
) -> ReportJsonResponse:
    return ReportJsonResponse(
        job_id="test",
        status="completed",
        completed_at=datetime.now(timezone.utc),
        total_pipeline_ms=100,
        recommendations=recommendations or [],
        conflicts_resolved=conflicts_resolved or [],
        community=CommunityMetrics(
            commits_per_week=3.0,
            unique_contributors=2,
            is_degraded=community_is_degraded,
        ),
        file_heatmap=file_heatmap,
        guardrail_telemetry=None,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_self_check_detects_empty_recommendations_with_high_complexity():
    reporter = Reporter()
    ctx = _make_ctx(static=_make_static())
    draft = _make_draft(recommendations=[])
    warnings = reporter._self_check(draft, ctx)
    assert any("recommendations" in w for w in warnings), (
        "Should warn when high-complexity functions exist but recommendations is empty"
    )


def test_self_check_detects_missing_file_heatmap_with_high_complexity():
    from app.models.agent_schemas import Recommendation as Rec
    reporter = Reporter()
    ctx = _make_ctx(static=_make_static())
    rec = Rec(title="Refactor do_thing", detail="x", affected_files=["utils.py"], priority=RiskLevel.HIGH)
    draft = _make_draft(recommendations=[rec], file_heatmap=None)
    warnings = reporter._self_check(draft, ctx)
    assert any("file_heatmap" in w for w in warnings), (
        "Should warn when high-complexity functions exist but file_heatmap is None"
    )


def test_self_check_detects_orphan_conflict_module():
    reporter = Reporter()
    ctx = _make_ctx()
    orphan_conflict = ConflictResolution(
        module="nonexistent_module.py",
        static_view="high risk",
        behavior_view="unused",
        final_recommendation="remove it",
    )
    draft = _make_draft(conflicts_resolved=[orphan_conflict])
    warnings = reporter._self_check(draft, ctx)
    assert any("nonexistent_module.py" in w for w in warnings), (
        "Should warn when conflict references a module not in static or behavior results"
    )


def test_self_check_passes_on_normal_report():
    from app.models.agent_schemas import Recommendation as Rec, LineRisk
    from app.models.api_schemas import LineRiskHttp

    reporter = Reporter()
    static = _make_static()
    ctx = _make_ctx(static=static)

    rec = Rec(
        title="Refactor do_thing",
        detail="Split the function.",
        affected_files=["utils.py"],
        priority=RiskLevel.HIGH,
    )
    draft = _make_draft(
        recommendations=[rec],
        file_heatmap={"utils.py": []},
        conflicts_resolved=[],
        community_is_degraded=False,
    )
    warnings = reporter._self_check(draft, ctx)
    assert warnings == [], f"Expected no warnings on a valid draft, got: {warnings}"


def test_self_check_detects_non_positive_pipeline_ms():
    reporter = Reporter()
    ctx = _make_ctx()
    draft = _make_draft()
    draft.total_pipeline_ms = 0
    warnings = reporter._self_check(draft, ctx)
    assert any("total_pipeline_ms" in w for w in warnings)


def test_self_check_community_degraded_not_propagated():
    reporter = Reporter()
    community = _make_community(is_degraded=True)
    ctx = _make_ctx(community=community)
    draft = _make_draft(community_is_degraded=False)
    warnings = reporter._self_check(draft, ctx)
    assert any("community" in w for w in warnings), (
        "Should warn when community is degraded but draft community.is_degraded is False"
    )


@pytest.mark.asyncio
async def test_render_injects_self_check_warnings_into_telemetry():
    """render() must attach self_check_warnings to guardrail_telemetry when warnings exist."""
    static = StaticResult(
        job_id="test",
        high_complexity_functions=[
            FunctionRisk(file="app.py", line=1, name="f", cc=20, risk_level=RiskLevel.CRITICAL, suggestion="x")
        ],
        low_coverage_modules=[],
        file_heatmap={},
        pylint_scores={},
        total_files_scanned=1,
        duration_ms=10,
    )
    behavior = BehaviorResult(
        job_id="test", usage_patterns=[], core_modules=[],
        inference_evidence={}, guardrail_passed=True, duration_ms=5,
    )
    community = CommunityResult(job_id="test", commits_per_week=1.0, unique_contributors=1, duration_ms=5)
    ctx = ReporterInput(
        job_id="test", repo_path="/tmp",
        static_result=static, behavior_result=behavior, community_result=community,
    )
    reporter = Reporter()
    result = await reporter.render(ctx)
    assert result.guardrail_telemetry is not None
    assert isinstance(result.guardrail_telemetry.self_check_warnings, list)
    assert any("file_heatmap" in w for w in result.guardrail_telemetry.self_check_warnings), (
        "Expected warning about missing file_heatmap since heatmap is empty but high CC exists"
    )
