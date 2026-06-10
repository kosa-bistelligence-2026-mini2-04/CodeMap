from __future__ import annotations

import pytest

from app.models.agent_schemas import (
    BehaviorResult,
    CommunityResult,
    ConflictResolution,
    FunctionRisk,
    LineRisk,
    ModuleCoverage,
    Recommendation,
    ReportResult,
    RiskLevel,
    StaticAnalyzerInput,
    StaticResult,
)
from app.models.api_schemas import AnalyzeRequest, AnalyzeResponse
from datetime import datetime, timezone


def test_risk_level_values():
    assert RiskLevel.LOW == "low"
    assert RiskLevel.HIGH == "high"
    assert RiskLevel.CRITICAL == "critical"


def test_function_risk_construction():
    fr = FunctionRisk(
        file="src/utils.py",
        line=42,
        name="utils.parse_config",
        cc=12,
        risk_level=RiskLevel.HIGH,
        suggestion="Extract sub-functions to reduce CC.",
    )
    assert fr.cc == 12
    assert fr.risk_level == RiskLevel.HIGH


def test_module_coverage_construction():
    mc = ModuleCoverage(path="src/utils.py", coverage_pct=55.0, uncovered_lines=[10, 20])
    assert mc.coverage_pct == 55.0
    assert 10 in mc.uncovered_lines


def test_line_risk_construction():
    lr = LineRisk(line=5, risk_level=RiskLevel.MEDIUM, reason="Complex branch")
    assert lr.line == 5


def test_recommendation_construction():
    rec = Recommendation(
        title="Refactor parse_config",
        detail="CC=18 exceeds threshold.",
        affected_files=["config/parser.py"],
        priority=RiskLevel.HIGH,
    )
    assert rec.priority == RiskLevel.HIGH


def test_static_analyzer_input_defaults():
    inp = StaticAnalyzerInput(repo_path="/tmp/repo", job_id="abc-123")
    assert inp.timeout_seconds == 60
    assert inp.cc_threshold == 10


def test_static_result_construction():
    sr = StaticResult(
        job_id="job-1",
        high_complexity_functions=[],
        low_coverage_modules=[],
        file_heatmap={},
        pylint_scores={},
        total_files_scanned=10,
        duration_ms=500,
    )
    assert sr.total_files_scanned == 10


def test_behavior_result_construction():
    br = BehaviorResult(
        job_id="job-1",
        usage_patterns=["pattern A"],
        core_modules=["utils"],
        inference_evidence={"pattern A": "README line 5"},
        guardrail_passed=True,
        duration_ms=1000,
    )
    assert br.guardrail_passed is True


def test_community_result_construction():
    cr = CommunityResult(
        job_id="job-1",
        commits_per_week=3.5,
        unique_contributors=5,
        duration_ms=200,
    )
    assert cr.is_degraded is False
    assert cr.avg_issue_response_hours is None


def test_conflict_resolution_construction():
    conf = ConflictResolution(
        module="utils",
        static_view="CC=15, coverage=42%",
        behavior_view="Referenced in 3 usage patterns",
        final_recommendation="Increase test coverage before refactor.",
    )
    assert conf.module == "utils"


def test_report_result_construction():
    from app.models.agent_schemas import BehaviorResult, CommunityResult, StaticResult

    rr = ReportResult(
        job_id="job-1",
        html_report="<html></html>",
        recommendations=[
            Recommendation(title="A", detail="detail A"),
            Recommendation(title="B", detail="detail B"),
            Recommendation(title="C", detail="detail C"),
        ],
        duration_ms=800,
        total_pipeline_ms=5000,
    )
    assert len(rr.recommendations) == 3


def test_analyze_request_construction():
    req = AnalyzeRequest(source="github", path="https://github.com/owner/repo")
    assert req.source == "github"


def test_analyze_response_construction():
    resp = AnalyzeResponse(
        job_id="abc-123",
        status="queued",
        created_at=datetime.now(timezone.utc),
        ws_url="/ws/progress/abc-123",
    )
    assert resp.status == "queued"


# test_ws_message_construction removed: WSMessage was deleted in阶段2 patch
# (BUG-008 — was defined but never instantiated, flat push format used instead).
