from __future__ import annotations

import pytest

from app.models.api_schemas import GuardrailRegexBlock, GuardrailTelemetry
from app.services.observability import ObservabilityCollector


def _make_telemetry(regex=0, semantic=0, fallback=False) -> GuardrailTelemetry:
    return GuardrailTelemetry(
        regex_blocked=[
            GuardrailRegexBlock(original_text="x", rule_id="absolute") for _ in range(regex)
        ],
        semantic_filtered=[],
        fallback_triggered=fallback,
    )


def test_record_and_compute_p50_p95():
    obs = ObservabilityCollector()
    for ms in [1000, 2000, 3000, 4000, 5000]:
        obs.record_pipeline("j", ms, {}, _make_telemetry(), 1)

    m = obs.compute_metrics()
    assert m["pipeline_p50_s"] == pytest.approx(3.0, abs=0.1)
    assert m["pipeline_p95_s"] == pytest.approx(5.0, abs=0.1)
    assert m["total_pipelines"] == 5


def test_guardrail_hit_rate():
    obs = ObservabilityCollector()
    obs.record_pipeline("j1", 1000, {}, _make_telemetry(regex=2), 0)
    obs.record_pipeline("j2", 1000, {}, _make_telemetry(regex=0), 0)

    m = obs.compute_metrics()
    assert m["guardrail_regex_hit_rate"] == pytest.approx(1.0, abs=0.1)


def test_fallback_triggered_count():
    obs = ObservabilityCollector()
    obs.record_pipeline("j1", 500, {}, _make_telemetry(fallback=True), 0)
    obs.record_pipeline("j2", 500, {}, _make_telemetry(fallback=False), 0)

    m = obs.compute_metrics()
    assert m["fallback_triggered_count"] == 1


def test_prometheus_format_contains_core_metrics():
    obs = ObservabilityCollector()
    obs.record_pipeline("j1", 5000, {}, _make_telemetry(regex=1, fallback=True), 3)

    output = obs.prometheus_format()
    assert "repoinsight_pipeline_duration_seconds_bucket" in output
    assert "repoinsight_guardrail_regex_hits_total 1" in output
    assert "repoinsight_fallback_triggered_total 1" in output
    assert "repoinsight_cache_hit_rate" in output
