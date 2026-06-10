from __future__ import annotations

import asyncio
import os
import shutil
import tempfile
from typing import Literal


class RepoCloner:
    """Clones a GitHub URL or validates a local path into a read-only snapshot directory."""

    async def clone(
        self, source: Literal["local", "github"], path: str, job_id: str
    ) -> str:
        if source == "local":
            if not os.path.isabs(path):
                raise ValueError("local source requires absolute path")
            if not os.path.exists(path):
                raise FileNotFoundError(path)
            return path

        # github
        # BUG-R2 fix: use --shallow-since instead of --depth=1 so CommunityAssessor
        # has enough history to compute commits_per_week over the 30-day window.
        tmp_dir = tempfile.mkdtemp(prefix=f"repo_insight_{job_id}_")
        proc = await asyncio.create_subprocess_exec(
            "git",
            "clone",
            "--shallow-since=35 days ago",
            "--single-branch",
            path,
            tmp_dir,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode != 0:
            # Fall back to --depth=50 if --shallow-since fails (rare git versions
            # or repos with no commits in the window). Still better than depth=1.
            shutil.rmtree(tmp_dir, ignore_errors=True)
            tmp_dir = tempfile.mkdtemp(prefix=f"repo_insight_{job_id}_")
            proc = await asyncio.create_subprocess_exec(
                "git",
                "clone",
                "--depth=50",
                "--single-branch",
                path,
                tmp_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            if proc.returncode != 0:
                shutil.rmtree(tmp_dir, ignore_errors=True)
                raise RuntimeError(f"git clone failed: {stderr.decode()}")
        os.chmod(tmp_dir, 0o555)  # read-only after clone
        return tmp_dir

    async def cleanup(self, path: str, source: Literal["local", "github"]) -> None:
        if source == "local":
            return  # no-op for user files
        try:
            os.chmod(path, 0o755)
        except Exception:
            pass
        shutil.rmtree(path, ignore_errors=True)

    # Keep backward-compatible resolve/cleanup(path) signatures used by old stub callers
    async def resolve(self, source: str, path: str) -> str:
        """Legacy alias — delegates to clone with a placeholder job_id."""
        return await self.clone(source, path, job_id="legacy")  # type: ignore[arg-type]
