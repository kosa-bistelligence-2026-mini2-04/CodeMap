from __future__ import annotations

import inspect
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest

from app.agents.reporter import Reporter
from app.models.agent_schemas import (
    BehaviorResult,
    CommunityResult,
    FunctionRisk,
    ReporterInput,
    RiskLevel,
    StaticResult,
)
from app.models.api_schemas import (
    CommunityMetrics,
    GuardrailRegexBlock,
    GuardrailSemanticFilter,
    GuardrailTelemetry,
    ReportJsonResponse,
)
from app.orchestrator.conflict_resolver import ConflictResolver


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_ctx(
    job_id="test",
    core_modules=None,
    high_cc_file="utils.py",
    high_cc=15,
    guardrail_telemetry=None,
) -> ReporterInput:
    static = StaticResult(
        job_id=job_id,
        high_complexity_functions=[
            FunctionRisk(
                file=high_cc_file,
                line=10,
                name="do_thing",
                cc=high_cc,
                risk_level=RiskLevel.HIGH,
                suggestion="Refactor this.",
            )
        ],
        low_coverage_modules=[],
        file_heatmap={},
        pylint_scores={},
        total_files_scanned=1,
        duration_ms=100,
    )
    behavior = BehaviorResult(
        job_id=job_id,
        usage_patterns=["Use case A"],
        core_modules=core_modules or [],
        inference_evidence={},
        guardrail_passed=True,
        duration_ms=200,
    )
    community = CommunityResult(
        job_id=job_id,
        commits_per_week=5.0,
        unique_contributors=3,
        duration_ms=50,
    )
    return ReporterInput(
        job_id=job_id,
        repo_path="/tmp/repo",
        static_result=static,
        behavior_result=behavior,
        community_result=community,
        guardrail_telemetry=guardrail_telemetry,
    )


# ---------------------------------------------------------------------------
# T5 Test 1: Output field set matches ReportJsonResponse schema
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_render_output_field_set_matches_schema():
    reporter = Reporter()
    ctx = _make_ctx()
    result = await reporter.render(ctx)
    schema_fields = set(ReportJsonResponse.model_fields.keys())
    result_fields = set(result.model_dump().keys())
    assert result_fields == schema_fields, f"Field mismatch: {result_fields ^ schema_fields}"


# ---------------------------------------------------------------------------
# Executive summary LLM call
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_executive_summary_uses_llm_when_provider_set():
    """When llm_provider is wired, Reporter calls it for a structured JSON summary."""
    mock_llm = AsyncMock()
    mock_llm.complete.return_value = (
        '{"summary": "这是一个中型 HTTP 客户端库，代码质量整体良好但复杂度偏高。",'
        ' "health_score": 72,'
        ' "key_strengths": ["文档清晰", "API 稳定"],'
        ' "key_risks": ["部分函数复杂度超阈值"],'
        ' "confidence": 0.85}'
    )
    reporter = Reporter(llm_provider=mock_llm, cache=None, guardrail=None)
    ctx = _make_ctx()

    result = await reporter.render(ctx)

    assert result.executive_summary is not None
    assert "HTTP" in result.executive_summary
    assert result.health_score == 72
    assert "文档清晰" in result.key_strengths
    assert result.summary_confidence == 0.85
    mock_llm.complete.assert_called_once()
    kwargs = mock_llm.complete.call_args.kwargs
    # Summary uses the provider's default model (no explicit override) = gpt-5.4
    assert "model" not in kwargs
    # Enforces JSON output format
    assert kwargs.get("response_format") == {"type": "json_object"}
    # Prompt is Chinese and includes the top function
    assert "do_thing" in kwargs["prompt"]


@pytest.mark.asyncio
async def test_executive_summary_none_when_no_provider():
    """Without llm_provider, summary stays None — report still completes."""
    reporter = Reporter()  # no llm_provider
    ctx = _make_ctx()
    result = await reporter.render(ctx)
    assert result.executive_summary is None


@pytest.mark.asyncio
async def test_executive_summary_silent_failure_on_llm_error():
    """LLM errors must not block the report — summary is best-effort."""
    mock_llm = AsyncMock()
    mock_llm.complete.side_effect = RuntimeError("openai down")
    reporter = Reporter(llm_provider=mock_llm)
    ctx = _make_ctx()

    result = await reporter.render(ctx)

    assert result.executive_summary is None
    assert result.status == "completed"
    assert len(result.recommendations) > 0


# ---------------------------------------------------------------------------
# T5 Test 2: Recommendation priority upgrades on core_module overlap
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_recommendation_priority_upgrades_on_core_module_overlap():
    """When static flags utils.py high + behavior has utils in core_modules -> CRITICAL."""
    reporter = Reporter()
    ctx = _make_ctx(high_cc_file="utils.py", core_modules=["utils"])
    result = await reporter.render(ctx)
    assert result.recommendations, "Should have at least one recommendation"
    top_rec = result.recommendations[0]
    assert top_rec.priority == RiskLevel.CRITICAL, (
        f"Expected CRITICAL priority when module in core_modules, got {top_rec.priority}"
    )


# ---------------------------------------------------------------------------
# T5 Test 3: ConflictResolver results passed through
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_conflicts_resolved_passthrough():
    from app.models.agent_schemas import ConflictResolution

    mock_resolver = AsyncMock(spec=ConflictResolver)
    mock_resolver.resolve.return_value = [
        ConflictResolution(
            module="utils",
            static_view="high CC",
            behavior_view="core module",
            final_recommendation="Refactor incrementally.",
        )
    ]
    reporter = Reporter(conflict_resolver=mock_resolver)
    ctx = _make_ctx()
    result = await reporter.render(ctx)
    assert len(result.conflicts_resolved) == 1
    assert result.conflicts_resolved[0].module == "utils"


# ---------------------------------------------------------------------------
# T5 Test 4: guardrail_telemetry passthrough (3 paths)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_guardrail_telemetry_passthrough_regex_blocked():
    telemetry = GuardrailTelemetry(
        regex_blocked=[GuardrailRegexBlock(original_text="必须", rule_id="absolute")],
        fallback_triggered=False,
    )
    reporter = Reporter()
    ctx = _make_ctx(guardrail_telemetry=telemetry)
    result = await reporter.render(ctx)
    assert result.guardrail_telemetry is not None
    assert len(result.guardrail_telemetry.regex_blocked) == 1


@pytest.mark.asyncio
async def test_guardrail_telemetry_passthrough_semantic_filtered():
    telemetry = GuardrailTelemetry(
        semantic_filtered=[
            GuardrailSemanticFilter(original_text="hallucinated claim", similarity_score=0.1, threshold=0.35)
        ],
        fallback_triggered=False,
    )
    reporter = Reporter()
    ctx = _make_ctx(guardrail_telemetry=telemetry)
    result = await reporter.render(ctx)
    assert result.guardrail_telemetry is not None
    assert len(result.guardrail_telemetry.semantic_filtered) == 1


@pytest.mark.asyncio
async def test_guardrail_telemetry_passthrough_fallback_triggered():
    telemetry = GuardrailTelemetry(fallback_triggered=True)
    reporter = Reporter()
    ctx = _make_ctx(guardrail_telemetry=telemetry)
    result = await reporter.render(ctx)
    assert result.guardrail_telemetry is not None
    assert result.guardrail_telemetry.fallback_triggered is True


# ---------------------------------------------------------------------------
# T5 Test 5: ECharts config embedded as data attribute in html_report
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_echarts_config_embedded_as_data_attribute():
    from app.models.agent_schemas import LineRisk
    from app.models.api_schemas import LineRiskHttp

    static = StaticResult(
        job_id="test",
        high_complexity_functions=[
            FunctionRisk(file="app.py", line=5, name="fn", cc=12, risk_level=RiskLevel.HIGH, suggestion="x")
        ],
        low_coverage_modules=[],
        file_heatmap={"app.py": [LineRisk(line=5, risk_level=RiskLevel.HIGH, reason="CC=12")]},
        pylint_scores={},
        total_files_scanned=1,
        duration_ms=100,
    )
    behavior = BehaviorResult(
        job_id="test", usage_patterns=[], core_modules=[],
        inference_evidence={}, guardrail_passed=True, duration_ms=10,
    )
    community = CommunityResult(
        job_id="test", commits_per_week=1.0, unique_contributors=1, duration_ms=5,
    )
    ctx = ReporterInput(
        job_id="test", repo_path="/tmp", static_result=static,
        behavior_result=behavior, community_result=community,
    )
    reporter = Reporter()
    result = await reporter.render(ctx)
    assert result.html_report is not None
    assert "data-echarts-config='" in result.html_report, (
        "html_report must contain ECharts config as data-echarts-config attribute"
    )


# ---------------------------------------------------------------------------
# T5 Test 6: html_report does not import jinja2
# ---------------------------------------------------------------------------

def test_html_report_no_jinja():
    import app.agents.reporter as reporter_module
    source = inspect.getsource(reporter_module)
    assert "jinja2" not in source.lower(), "reporter.py must not import jinja2"
    assert "import jinja" not in source, "reporter.py must not import jinja"
