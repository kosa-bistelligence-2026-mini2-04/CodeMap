"""Tests for P0-4: ConflictResolver judge model routing.

Verifies that:
- Default path uses gpt-5.4-nano
- Low confidence (<0.6) triggers escalation to high-tier model
- Escalated ConflictResolution has escalated=True and correct judge_model
- Per-model cost tracking works correctly
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.agent_schemas import (
    BehaviorResult,
    ConflictResolution,
    FunctionRisk,
    RiskLevel,
    StaticResult,
)
from app.orchestrator.conflict_resolver import ConflictResolver
from app.services.observability import ObservabilityCollector


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_static_result(module_file: str = "utils.py") -> StaticResult:
    return StaticResult(
        job_id="test-job",
        high_complexity_functions=[
            FunctionRisk(
                file=module_file,
                line=10,
                name="complex_func",
                cc=15,
                risk_level=RiskLevel.HIGH,
                suggestion="Refactor into smaller functions",
            )
        ],
        low_coverage_modules=[],
        file_heatmap={},
        pylint_scores={},
        total_files_scanned=1,
        duration_ms=100,
    )


def _make_behavior_result(core_module: str = "utils") -> BehaviorResult:
    return BehaviorResult(
        job_id="test-job",
        usage_patterns=["pattern one"],
        core_modules=[core_module],
        inference_evidence={},
        guardrail_passed=True,
        guardrail_warnings=[],
        duration_ms=50,
    )


def _llm_response(verdict: str = "monitor", confidence: float = 0.8) -> str:
    return json.dumps({
        "verdict": verdict,
        "rationale": "Test rationale under 80 chars",
        "action": "Review code",
        "final_recommendation": f"Module is {verdict}. Review carefully.",
        "confidence": confidence,
    })


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestDefaultUsesMini:
    @pytest.mark.asyncio
    async def test_default_uses_mini(self):
        """High-confidence primary response must use gpt-5.4-nano and not escalate."""
        mock_provider = AsyncMock()
        mock_provider.complete = AsyncMock(return_value=_llm_response(confidence=0.8))

        resolver = ConflictResolver(llm_provider=mock_provider)
        static = _make_static_result("utils.py")
        behavior = _make_behavior_result("utils")

        results = await resolver.resolve(static, behavior)

        assert len(results) == 1
        resolution = results[0]
        assert resolution.judge_model == "gpt-5.4-nano"
        assert resolution.escalated is False
        assert resolution.confidence == pytest.approx(0.8)

        # Verify model= parameter was gpt-5.4-nano on the call
        call_kwargs = mock_provider.complete.call_args
        assert call_kwargs.kwargs.get("model") == "gpt-5.4-nano"

    @pytest.mark.asyncio
    async def test_high_confidence_no_escalation(self):
        """High confidence must result in exactly one LLM call."""
        mock_provider = AsyncMock()
        mock_provider.complete = AsyncMock(return_value=_llm_response(confidence=0.9))

        resolver = ConflictResolver(llm_provider=mock_provider)
        static = _make_static_result("utils.py")
        behavior = _make_behavior_result("utils")

        await resolver.resolve(static, behavior)

        assert mock_provider.complete.call_count == 1


class TestLowConfidenceEscalates:
    @pytest.mark.asyncio
    async def test_low_confidence_escalates(self):
        """Primary response with confidence<0.6 must trigger escalation to high-tier model."""
        escalation_response = _llm_response(verdict="refactor_priority", confidence=0.85)

        call_count = 0

        async def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            model = kwargs.get("model", "")
            if model == ConflictResolver.PRIMARY_MODEL:
                return _llm_response(confidence=0.3)
            return escalation_response

        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = side_effect

        resolver = ConflictResolver(llm_provider=mock_provider)
        static = _make_static_result("utils.py")
        behavior = _make_behavior_result("utils")

        results = await resolver.resolve(static, behavior)

        assert len(results) == 1
        resolution = results[0]
        assert resolution.escalated is True
        assert resolution.judge_model == ConflictResolver.ESCALATION_MODEL
        assert resolution.confidence == pytest.approx(0.85)
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_escalation_model_is_called_second(self):
        """On escalation the second call must use ESCALATION_MODEL, not PRIMARY_MODEL."""
        call_models: list[str] = []

        async def side_effect(*args, **kwargs):
            model = kwargs.get("model", "")
            call_models.append(model)
            if model == ConflictResolver.PRIMARY_MODEL:
                return _llm_response(confidence=0.2)
            return _llm_response(confidence=0.9)

        mock_provider = AsyncMock()
        mock_provider.complete.side_effect = side_effect

        resolver = ConflictResolver(llm_provider=mock_provider)
        static = _make_static_result("utils.py")
        behavior = _make_behavior_result("utils")

        await resolver.resolve(static, behavior)

        assert len(call_models) == 2
        assert call_models[0] == ConflictResolver.PRIMARY_MODEL
        assert call_models[1] == ConflictResolver.ESCALATION_MODEL


class TestCostTrackingByModel:
    def test_cost_tracking_by_model(self):
        """record_llm_call must accumulate costs separately per model."""
        obs = ObservabilityCollector()

        obs.record_llm_call(model="gpt-5.4-nano", prompt_tokens=1000, completion_tokens=200)
        obs.record_llm_call(model="gpt-5.4-nano", prompt_tokens=500, completion_tokens=100)
        obs.record_llm_call(model="gpt-5.4", prompt_tokens=1000, completion_tokens=300)

        assert "gpt-5.4-nano" in obs._llm_cost_usd_by_model
        assert "gpt-5.4" in obs._llm_cost_usd_by_model
        assert obs._llm_cost_usd_by_model["gpt-5.4-nano"] > 0
        assert obs._llm_cost_usd_by_model["gpt-5.4"] > 0
        # Mini should cost less than high-tier for same token count
        assert obs._llm_cost_usd_by_model["gpt-5.4-nano"] < obs._llm_cost_usd_by_model["gpt-5.4"]

    def test_total_cost_equals_sum_of_model_costs(self):
        """Total accumulated cost must equal the sum of per-model costs."""
        obs = ObservabilityCollector()
        obs.record_llm_call(model="gpt-5.4-nano", prompt_tokens=1000, completion_tokens=200)
        obs.record_llm_call(model="gpt-5.4", prompt_tokens=800, completion_tokens=150)

        total_from_models = sum(obs._llm_cost_usd_by_model.values())
        assert obs._llm_cost_usd == pytest.approx(total_from_models)

    def test_prometheus_format_includes_model_labels(self):
        """prometheus_format must emit labeled cost lines per model."""
        obs = ObservabilityCollector()
        obs.record_llm_call(model="gpt-5.4-nano", prompt_tokens=1000, completion_tokens=100)
        obs.record_llm_call(model="gpt-5.4", prompt_tokens=500, completion_tokens=50)

        metrics = obs.prometheus_format()
        assert 'repoinsight_llm_cost_usd{model="gpt-5.4-nano"}' in metrics
        assert 'repoinsight_llm_cost_usd{model="gpt-5.4"}' in metrics

    @pytest.mark.asyncio
    async def test_no_provider_returns_default_resolution(self):
        """ConflictResolver without llm_provider must return a safe default with correct fields."""
        resolver = ConflictResolver(llm_provider=None)
        static = _make_static_result("utils.py")
        behavior = _make_behavior_result("utils")

        results = await resolver.resolve(static, behavior)

        assert len(results) == 1
        r = results[0]
        assert r.judge_model == ConflictResolver.PRIMARY_MODEL
        assert r.escalated is False
        assert 0.0 <= r.confidence <= 1.0
