from __future__ import annotations

import asyncio
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.community_assessor import CommunityAssessor
from app.models.agent_schemas import CommunityAssessorInput


def _make_input(**kwargs) -> CommunityAssessorInput:
    defaults = dict(repo_path="/tmp/repo", job_id="test-job", lookback_days=30)
    defaults.update(kwargs)
    return CommunityAssessorInput(**defaults)


def _mock_proc(stdout: bytes) -> MagicMock:
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(stdout, b""))
    proc.returncode = 0
    return proc


GIT_LOG_OUTPUT = (
    b"abc123\x1falice@example.com\x1f2026-03-01 10:00:00 +0000\n"
    b"def456\x1fbob@example.com\x1f2026-03-05 11:00:00 +0000\n"
    b"ghi789\x1falice@example.com\x1f2026-03-10 12:00:00 +0000\n"
    b"jkl012\x1fcharlie@example.com\x1f2026-03-15 13:00:00 +0000\n"
    b"mno345\x1falice@example.com\x1f2026-03-20 14:00:00 +0000\n"
    b"pqr678\x1fbob@example.com\x1f2026-03-25 15:00:00 +0000"
)


@pytest.mark.asyncio
async def test_git_log_parsing():
    """Parses git log output: unique_contributors and top_contributors are correct."""
    assessor = CommunityAssessor()
    proc = _mock_proc(GIT_LOG_OUTPUT + b"\n")

    with patch("asyncio.create_subprocess_exec", return_value=proc):
        commits_per_week, unique_contributors, top_contributors = (
            await assessor._parse_git_log("/tmp/repo", 30)
        )

    assert unique_contributors == 3
    assert top_contributors[0] == "alice@example.com"
    assert "bob@example.com" in top_contributors
    assert "charlie@example.com" in top_contributors


@pytest.mark.asyncio
async def test_commits_per_week_calculation():
    """6 commits / 30 days == 1.4 commits per week."""
    assessor = CommunityAssessor()
    proc = _mock_proc(GIT_LOG_OUTPUT + b"\n")

    with patch("asyncio.create_subprocess_exec", return_value=proc):
        commits_per_week, _, _ = await assessor._parse_git_log("/tmp/repo", 30)

    assert abs(commits_per_week - 6 / (30 / 7.0)) < 1e-9


@pytest.mark.asyncio
async def test_no_github_token_skips_issue_api(monkeypatch):
    """When GITHUB_TOKEN is absent, avg_issue_response_hours is None without any HTTP call."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)

    assessor = CommunityAssessor()
    proc = _mock_proc(GIT_LOG_OUTPUT + b"\n")

    with patch("asyncio.create_subprocess_exec", return_value=proc):
        with patch("aiohttp.ClientSession") as mock_session:
            result = await assessor.run(_make_input(github_token=None))

    mock_session.assert_not_called()
    assert result.avg_issue_response_hours is None


@pytest.mark.asyncio
async def test_budget_timeout_propagates():
    """asyncio.TimeoutError from git log bubbles up — CommunityAssessor does NOT degrade."""
    assessor = CommunityAssessor()

    async def _hanging(*args, **kwargs):
        await asyncio.sleep(9999)

    proc = MagicMock()
    proc.communicate = _hanging

    with patch("asyncio.create_subprocess_exec", return_value=proc):
        with pytest.raises(asyncio.TimeoutError):
            await assessor.run(_make_input(timeout_seconds=1))


@pytest.mark.asyncio
async def test_github_token_calls_aiohttp(monkeypatch):
    """When GITHUB_TOKEN is present, aiohttp is called with correct URL and timeout."""
    monkeypatch.setenv("GITHUB_TOKEN", "test-token-xyz")

    assessor = CommunityAssessor()
    proc = _mock_proc(b"")  # zero commits, valid response

    mock_response = AsyncMock()
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=[])

    mock_session_inst = AsyncMock()
    mock_session_inst.__aenter__ = AsyncMock(return_value=mock_session_inst)
    mock_session_inst.__aexit__ = AsyncMock(return_value=False)
    mock_session_inst.get = MagicMock(return_value=mock_response)

    import aiohttp

    with patch("asyncio.create_subprocess_exec", return_value=proc):
        with patch("aiohttp.ClientSession", return_value=mock_session_inst) as mock_cls:
            with patch("aiohttp.ClientTimeout") as mock_timeout:
                await assessor.run(
                    _make_input(
                        repo_path="https://github.com/owner/myrepo",
                        github_token="test-token-xyz",
                    )
                )

    mock_timeout.assert_called_once_with(total=15)


# ---------------------------------------------------------------------------
# BUG-R2: Empty git log returns 0 commits (30-day window with no commits)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_empty_git_log_returns_zero():
    """When git log returns no lines, commits_per_week and unique_contributors are 0."""
    assessor = CommunityAssessor()
    proc = _mock_proc(b"")

    with patch("asyncio.create_subprocess_exec", return_value=proc):
        commits_per_week, unique_contributors, top_contributors = (
            await assessor._parse_git_log("/tmp/repo", 30)
        )

    assert commits_per_week == 0.0
    assert unique_contributors == 0
    assert top_contributors == []


@pytest.mark.asyncio
async def test_non_git_repo_returns_degraded():
    """When git log returns non-zero with 'not a git repository', result is degraded."""
    assessor = CommunityAssessor()

    proc = MagicMock()
    proc.returncode = 128
    proc.communicate = AsyncMock(
        return_value=(b"", b"fatal: not a git repository (or any of the parent directories): .git")
    )

    with patch("asyncio.create_subprocess_exec", return_value=proc):
        result = await assessor.run(_make_input())

    assert result.is_degraded is True
    assert result.commits_per_week == 0.0
    assert result.unique_contributors == 0
    assert result.degraded_reason is not None
    assert "not a git repository" in result.degraded_reason


@pytest.mark.asyncio
async def test_git_log_pipe_in_email_does_not_break_parsing():
    """Commit message containing '|' must not corrupt email parsing with new \x1f separator."""
    # Simulate a scenario where an old-style pipe was in some field but we use \x1f now
    log_output = (
        b"abc123\x1fdev|extra@example.com\x1f2026-03-01 10:00:00 +0000\n"
        b"def456\x1fclean@example.com\x1f2026-03-05 11:00:00 +0000\n"
    )
    assessor = CommunityAssessor()
    proc = _mock_proc(log_output)

    with patch("asyncio.create_subprocess_exec", return_value=proc):
        commits_per_week, unique_contributors, top_contributors = (
            await assessor._parse_git_log("/tmp/repo", 30)
        )

    assert unique_contributors == 2
    assert "dev|extra@example.com" in top_contributors
    assert "clean@example.com" in top_contributors
