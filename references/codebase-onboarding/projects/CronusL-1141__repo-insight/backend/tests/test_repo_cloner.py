from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from unittest.mock import AsyncMock, MagicMock, call, patch

import pytest

from app.services.repo_cloner import RepoCloner


def _mock_proc(returncode: int = 0, stderr: bytes = b"") -> MagicMock:
    proc = MagicMock()
    proc.communicate = AsyncMock(return_value=(b"", stderr))
    proc.returncode = returncode
    return proc


@pytest.mark.asyncio
async def test_local_absolute_path_returns_as_is(tmp_path):
    """clone('local', abs_path) returns the path unchanged."""
    cloner = RepoCloner()
    result = await cloner.clone("local", str(tmp_path), "job-1")
    assert result == str(tmp_path)


@pytest.mark.asyncio
async def test_local_relative_path_raises():
    """clone('local', relative_path) raises ValueError."""
    cloner = RepoCloner()
    with pytest.raises(ValueError, match="absolute path"):
        await cloner.clone("local", "relative/path", "job-1")


@pytest.mark.asyncio
async def test_github_clone_subprocess_args():
    """BUG-R2 fix: clone('github', ...) uses --shallow-since for 30-day community window."""
    cloner = RepoCloner()
    proc = _mock_proc(returncode=0)

    with patch("asyncio.create_subprocess_exec", return_value=proc) as mock_exec:
        with patch("tempfile.mkdtemp", return_value="/tmp/repo_insight_job-2_abc"):
            with patch("os.chmod"):
                result = await cloner.clone("github", "https://github.com/owner/repo", "job-2")

    args = mock_exec.call_args[0]
    assert "git" in args
    assert "clone" in args
    assert "--shallow-since=35 days ago" in args
    assert "--single-branch" in args
    assert result == "/tmp/repo_insight_job-2_abc"


@pytest.mark.asyncio
async def test_github_clone_failure_cleans_tmp():
    """On git clone failure (both shallow-since and depth=50 fallback), tmp_dir is removed."""
    cloner = RepoCloner()
    proc = _mock_proc(returncode=1, stderr=b"fatal: repository not found")
    tmp_dir = "/tmp/repo_insight_job-3_xyz"

    with patch("asyncio.create_subprocess_exec", return_value=proc):
        with patch("tempfile.mkdtemp", return_value=tmp_dir):
            with patch("shutil.rmtree") as mock_rmtree:
                with pytest.raises(RuntimeError, match="git clone failed"):
                    await cloner.clone("github", "https://github.com/owner/missing", "job-3")

    # Both the primary shallow-since clone and the depth=50 fallback clean up
    assert mock_rmtree.call_count == 2
    mock_rmtree.assert_called_with(tmp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_cleanup_local_is_noop(tmp_path):
    """cleanup('local') does not remove anything."""
    cloner = RepoCloner()
    with patch("shutil.rmtree") as mock_rmtree:
        await cloner.cleanup(str(tmp_path), "local")
    mock_rmtree.assert_not_called()


@pytest.mark.asyncio
async def test_cleanup_github_chmod_and_rmtree():
    """cleanup('github') calls chmod(0o755) then rmtree."""
    cloner = RepoCloner()
    path = "/tmp/repo_insight_job-4_aaa"

    with patch("os.chmod") as mock_chmod:
        with patch("shutil.rmtree") as mock_rmtree:
            await cloner.cleanup(path, "github")

    mock_chmod.assert_called_once_with(path, 0o755)
    mock_rmtree.assert_called_once_with(path, ignore_errors=True)


@pytest.mark.asyncio
async def test_chmod_read_only_after_clone():
    """After successful github clone, directory is chmod 0o555 (read-only)."""
    cloner = RepoCloner()
    proc = _mock_proc(returncode=0)
    tmp_dir = "/tmp/repo_insight_job-5_bbb"

    with patch("asyncio.create_subprocess_exec", return_value=proc):
        with patch("tempfile.mkdtemp", return_value=tmp_dir):
            with patch("os.chmod") as mock_chmod:
                await cloner.clone("github", "https://github.com/owner/repo", "job-5")

    mock_chmod.assert_called_once_with(tmp_dir, 0o555)
