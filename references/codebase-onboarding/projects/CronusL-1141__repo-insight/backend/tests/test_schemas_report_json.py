from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.agent_schemas import (
    BehaviorResult,
    CommunityResult,
    FunctionRisk,
    LineRisk,
    ModuleCoverage,
    Recommendation,
    RiskLevel,
    StaticResult,
)
from app.models.api_schemas import (
    CommunityMetrics,
    GuardrailRegexBlock,
    GuardrailSemanticFilter,
    GuardrailTelemetry,
    LineRiskHttp,
    ReportJsonResponse,
)


def _make_static() -> StaticResult:
    return StaticResult(
        job_id="job-1",
        high_complexity_functions=[
            FunctionRisk(
                file="app/utils.py",
                line=10,
                name="app.utils.do_thing",
                cc=12,
                risk_level=RiskLevel.HIGH,
                suggestion="Extract helper",
            )
        ],
        low_coverage_modules=[
            ModuleCoverage(path="app/utils.py", coverage_pct=45.0)
        ],
        file_heatmap={
            "app/utils.py": [
                LineRisk(line=10, risk_level=RiskLevel.HIGH, reason="high CC")
            ]
        },
        pylint_scores={"app/utils.py": 6.5},
        total_files_scanned=3,
        duration_ms=1200,
    )


def _make_behavior() -> BehaviorResult:
    return BehaviorResult(
        job_id="job-1",
        usage_patterns=["CLI invocation", "library import"],
        core_modules=["app/utils.py"],
        inference_evidence={"CLI invocation": "README line 5"},
        guardrail_passed=True,
        duration_ms=800,
    )


def _make_community() -> CommunityResult:
    return CommunityResult(
        job_id="job-1",
        commits_per_week=3.5,
        avg_issue_response_hours=12.0,
        unique_contributors=4,
        top_contributors=["alice", "bob"],
        is_degraded=False,
        duration_ms=300,
    )


def test_report_json_response_construction():
    """ReportJsonResponse can be constructed from typical agent results."""
    static = _make_static()
    behavior = _make_behavior()
    community = _make_community()

    report = ReportJsonResponse(
        job_id="job-1",
        completed_at=datetime.now(timezone.utc),
        total_pipeline_ms=static.duration_ms + behavior.duration_ms + community.duration_ms,
        recommendations=[
            Recommendation(title="Reduce CC", detail="Refactor utils.do_thing")
        ],
        community=CommunityMetrics(
            commits_per_week=community.commits_per_week,
            avg_issue_response_hours=community.avg_issue_response_hours,
            unique_contributors=community.unique_contributors,
            top_contributors=community.top_contributors,
            is_degraded=community.is_degraded,
        ),
        file_heatmap={
            fp: [LineRiskHttp(line=lr.line, risk_level=lr.risk_level, reason=lr.reason) for lr in lrs]
            for fp, lrs in static.file_heatmap.items()
        },
    )

    assert report.job_id == "job-1"
    assert report.status == "completed"
    assert report.total_pipeline_ms == 2300
    assert report.community.commits_per_week == 3.5
    assert report.community.is_degraded is False
    assert "app/utils.py" in report.file_heatmap
    assert report.file_heatmap["app/utils.py"][0].line == 10


def test_guardrail_telemetry_construction():
    """GuardrailTelemetry and sub-models can be constructed independently."""
    regex_block = GuardrailRegexBlock(
        original_text="This will happen in 2028",
        rule_id="future_tense",
    )
    assert regex_block.layer == "regex"

    semantic_filter = GuardrailSemanticFilter(
        original_text="unrelated hallucinated text",
        similarity_score=0.12,
        threshold=0.3,
    )
    assert semantic_filter.similarity_score < semantic_filter.threshold

    telemetry = GuardrailTelemetry(
        regex_blocked=[regex_block],
        semantic_filtered=[semantic_filter],
        regenerate_count=1,
        fallback_triggered=False,
    )
    assert len(telemetry.regex_blocked) == 1
    assert telemetry.regenerate_count == 1

    empty_telemetry = GuardrailTelemetry()
    assert empty_telemetry.regex_blocked == []
    assert empty_telemetry.semantic_filtered == []
    assert empty_telemetry.regenerate_count == 0
    assert empty_telemetry.fallback_triggered is False


def test_report_json_response_with_guardrail_telemetry():
    """ReportJsonResponse accepts guardrail_telemetry field."""
    community = _make_community()
    report = ReportJsonResponse(
        job_id="job-2",
        completed_at=datetime.now(timezone.utc),
        total_pipeline_ms=2000,
        recommendations=[],
        community=CommunityMetrics(
            commits_per_week=community.commits_per_week,
            unique_contributors=community.unique_contributors,
        ),
        guardrail_telemetry=GuardrailTelemetry(
            regex_blocked=[
                GuardrailRegexBlock(original_text="text", rule_id="rule-1")
            ],
            regenerate_count=2,
            fallback_triggered=True,
        ),
    )
    assert report.guardrail_telemetry is not None
    assert report.guardrail_telemetry.fallback_triggered is True
    assert report.guardrail_telemetry.regenerate_count == 2

    report_no_telemetry = ReportJsonResponse(
        job_id="job-3",
        completed_at=datetime.now(timezone.utc),
        total_pipeline_ms=1000,
        recommendations=[],
        community=CommunityMetrics(
            commits_per_week=1.0,
            unique_contributors=1,
        ),
    )
    assert report_no_telemetry.guardrail_telemetry is None


def test_report_json_response_field_snapshot():
    """Field set snapshot — for future diff against api.gen.ts ReportJsonResponse keys."""
    expected_fields = {
        "job_id",
        "status",
        "completed_at",
        "total_pipeline_ms",
        "recommendations",
        "conflicts_resolved",
        "community",
        "html_report",
        "file_heatmap",
        "guardrail_telemetry",
        "agent_durations",
        "executive_summary",
        "health_score",
        "key_strengths",
        "key_risks",
        "summary_confidence",
    }
    actual_fields = set(ReportJsonResponse.model_fields.keys())
    assert actual_fields == expected_fields, (
        f"Field drift detected. Missing: {expected_fields - actual_fields}, "
        f"Extra: {actual_fields - expected_fields}"
    )


# ---------------------------------------------------------------------------
# BUG-R0: agent_durations field
# ---------------------------------------------------------------------------

def test_agent_durations_field():
    """ReportJsonResponse accepts agent_durations dict and defaults to empty."""
    from datetime import datetime, timezone
    report = ReportJsonResponse(
        job_id="job-dur",
        completed_at=datetime.now(timezone.utc),
        total_pipeline_ms=5000,
        recommendations=[],
        community=CommunityMetrics(commits_per_week=2.0, unique_contributors=2),
        agent_durations={"static_analyzer": 30000, "behavior_inferer": 45000, "community_assessor": 10000},
    )
    assert report.agent_durations["static_analyzer"] == 30000
    assert report.agent_durations["behavior_inferer"] == 45000
    assert report.agent_durations["community_assessor"] == 10000

    report_default = ReportJsonResponse(
        job_id="job-dur2",
        completed_at=datetime.now(timezone.utc),
        total_pipeline_ms=1000,
        recommendations=[],
        community=CommunityMetrics(commits_per_week=1.0, unique_contributors=1),
    )
    assert report_default.agent_durations == {}
