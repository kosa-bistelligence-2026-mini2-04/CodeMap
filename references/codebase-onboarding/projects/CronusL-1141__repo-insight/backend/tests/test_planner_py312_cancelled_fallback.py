from __future__ import annotations

import asyncio

import pytest

from app.models.agent_schemas import CommunityResult
from app.orchestrator.planner import _handle_community
from app.orchestrator.timeout_guard import TimeoutGuard

JOB_ID = "test-job-001"
REPO_PATH = "/tmp/test-repo"


def _guard(tmp_path=None):
    db = str(tmp_path / "cache.db") if tmp_path else ":memory:"
    return TimeoutGuard(db_path=db)


@pytest.mark.asyncio
async def test_timeout_error_returns_degraded(tmp_path):
    """TimeoutError injection -> degraded CommunityResult with is_degraded=True."""
    exc = TimeoutError("simulated timeout")
    result = await _handle_community(exc, JOB_ID, REPO_PATH, _guard(tmp_path))
    assert isinstance(result, CommunityResult)
    assert result.is_degraded is True


@pytest.mark.asyncio
async def test_cancelled_error_is_reraised(tmp_path):
    """asyncio.CancelledError injection -> must raise, never degrade."""
    exc = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await _handle_community(exc, JOB_ID, REPO_PATH, _guard(tmp_path))


@pytest.mark.asyncio
async def test_runtime_error_returns_degraded(tmp_path):
    """Generic RuntimeError injection -> degraded CommunityResult (unexpected_error path)."""
    exc = RuntimeError("some unexpected failure")
    result = await _handle_community(exc, JOB_ID, REPO_PATH, _guard(tmp_path))
    assert isinstance(result, CommunityResult)
    assert result.is_degraded is True
