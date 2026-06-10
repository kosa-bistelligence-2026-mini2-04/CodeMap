"""Centralized pytest fixtures for the backend test suite.

These fixtures were extracted so that future test modules can build mock
results / stores / buses without duplicating boilerplate. Existing test
modules are NOT migrated to use them (to avoid touching a large number of
passing tests in this refactor pass) — only additive.
"""
from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from app.api.progress_bus import ProgressBus
from app.models.agent_schemas import (
    BehaviorResult,
    CommunityResult,
    FunctionRisk,
    RiskLevel,
    StaticResult,
)
from app.services.observability import ObservabilityCollector


# ---------------------------------------------------------------------------
# Agent result factories
# ---------------------------------------------------------------------------

@pytest.fixture
def static_result_factory():
    """Factory returning a StaticResult with one Top-N high-CC function.

    Usage:
        def test_x(static_result_factory):
            sr = static_result_factory(job_id="abc", cc=22)
    """
    def _make(
        job_id: str = "test",
        file: str = "utils.py",
        name: str = "do_thing",
        cc: int = 15,
    ) -> StaticResult:
        return StaticResult(
            job_id=job_id,
            high_complexity_functions=[
                FunctionRisk(
                    file=file,
                    line=10,
                    name=name,
                    cc=cc,
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

    return _make


@pytest.fixture
def behavior_result_factory():
    """Factory for a minimal BehaviorResult with guardrail_passed=True."""
    def _make(
        job_id: str = "test",
        core_modules: list[str] | None = None,
        patterns: list[str] | None = None,
    ) -> BehaviorResult:
        return BehaviorResult(
            job_id=job_id,
            usage_patterns=patterns or ["Use case A"],
            core_modules=core_modules or [],
            inference_evidence={},
            guardrail_passed=True,
            duration_ms=200,
        )

    return _make


@pytest.fixture
def community_result_factory():
    """Factory for a minimal CommunityResult (non-degraded by default)."""
    def _make(
        job_id: str = "test",
        commits: float = 5.0,
        contributors: int = 3,
        degraded: bool = False,
    ) -> CommunityResult:
        return CommunityResult(
            job_id=job_id,
            commits_per_week=commits,
            unique_contributors=contributors,
            is_degraded=degraded,
            duration_ms=50,
        )

    return _make


# ---------------------------------------------------------------------------
# Infra mocks / in-memory singletons
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_analysis_store():
    """AnalysisStore mock with all async methods stubbed as no-op coroutines."""
    store = AsyncMock()
    store.create_running = AsyncMock(return_value=None)
    store.mark_completed = AsyncMock(return_value=None)
    store.mark_failed = AsyncMock(return_value=None)
    store.get_report_json = AsyncMock(return_value=None)
    store.get_one = AsyncMock(return_value=None)
    store.list_recent = AsyncMock(return_value=[])
    store.count = AsyncMock(return_value=0)
    store.delete = AsyncMock(return_value=False)
    return store


@pytest.fixture
def in_memory_progress_bus() -> ProgressBus:
    """Fresh ProgressBus instance — useful for isolating publish/subscribe tests."""
    return ProgressBus()


@pytest.fixture
def observability_collector() -> ObservabilityCollector:
    """Fresh in-memory ObservabilityCollector (no Prometheus client required)."""
    return ObservabilityCollector()
