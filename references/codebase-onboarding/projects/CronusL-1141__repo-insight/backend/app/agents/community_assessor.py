from __future__ import annotations

import asyncio
import logging
import os
import time
from collections import Counter
from datetime import datetime, timezone
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

from app.agents.base import BaseAgent
from app.models.agent_schemas import CommunityAssessorInput, CommunityResult

if TYPE_CHECKING:
    pass


class _NotGitRepoError(Exception):
    """Raised when the target directory is not a git repository."""


_COMMUNITY_ANALYSIS_PROMPT = """你是 RepoInsight 社区健康评估 Agent。根据仓库近 30 天的 git 数据，产出一段中文的社区健康解读。

## 输入数据
- 每周提交次数：{commits_per_week}
- 近 30 天独立贡献者数：{contributors}
- 主要贡献者（邮箱）：{top}
- Issue 平均响应时间（小时）：{avg_response}
- 是否降级（git 数据不可用）：{degraded}

## 输出要求
- 中文，120-200 字
- 客观分析：活跃度水平、贡献者集中度、维护响应质量
- 指出健康度风险点（如果有）
- 禁止编造数据外的内容
- 不要 markdown 格式，不要代码块包裹
- 直接输出分析文本，不要前缀后缀

仅输出分析段落本身。
"""


class CommunityAssessor(BaseAgent):
    """Parses recent git log to compute community health metrics.

    Enhanced with an optional LLM analysis pass: after deterministic git data
    collection, the raw numbers are handed to an LLM for a short Chinese
    health-interpretation paragraph. LLM failure is non-blocking.
    """

    name = "community_assessor"

    def __init__(self, llm_provider=None, cache=None) -> None:
        self.llm_provider = llm_provider
        self.cache = cache

    async def run(self, input_data: CommunityAssessorInput) -> CommunityResult:
        start_ms = time.monotonic()

        async def _inner() -> CommunityResult:
            try:
                commits_per_week, unique_contributors, top_contributors = (
                    await self._parse_git_log(input_data.repo_path, input_data.lookback_days)
                )
            except _NotGitRepoError as exc:
                duration_ms = int((time.monotonic() - start_ms) * 1000)
                return CommunityResult(
                    job_id=input_data.job_id,
                    commits_per_week=0.0,
                    unique_contributors=0,
                    top_contributors=[],
                    is_degraded=True,
                    degraded_reason=f"not a git repository or git history unavailable: {exc}",
                    duration_ms=duration_ms,
                )

            github_token = input_data.github_token or os.environ.get("GITHUB_TOKEN")
            avg_issue_response_hours = await self._fetch_avg_issue_response(
                input_data.repo_path, github_token
            )

            llm_analysis = await self._generate_llm_analysis(
                commits_per_week=commits_per_week,
                unique_contributors=unique_contributors,
                top_contributors=top_contributors,
                avg_issue_response_hours=avg_issue_response_hours,
                is_degraded=False,
            )

            duration_ms = int((time.monotonic() - start_ms) * 1000)
            return CommunityResult(
                job_id=input_data.job_id,
                commits_per_week=commits_per_week,
                avg_issue_response_hours=avg_issue_response_hours,
                unique_contributors=unique_contributors,
                top_contributors=top_contributors,
                is_degraded=False,
                duration_ms=duration_ms,
                llm_analysis=llm_analysis,
            )

        return await asyncio.wait_for(_inner(), timeout=input_data.timeout_seconds)

    async def _generate_llm_analysis(
        self,
        commits_per_week: float,
        unique_contributors: int,
        top_contributors: list[str],
        avg_issue_response_hours: float | None,
        is_degraded: bool,
    ) -> str | None:
        """Best-effort LLM health interpretation. Returns None on any failure."""
        if self.llm_provider is None:
            return None

        prompt = _COMMUNITY_ANALYSIS_PROMPT.format(
            commits_per_week=f"{commits_per_week:.1f}",
            contributors=unique_contributors,
            top=", ".join(top_contributors[:5]) or "无",
            avg_response=f"{avg_issue_response_hours:.1f}" if avg_issue_response_hours is not None else "未知",
            degraded="是" if is_degraded else "否",
        )

        cache_key_str = None
        if self.cache is not None:
            import hashlib
            cache_key_str = "community_llm::" + hashlib.sha256(
                prompt.encode("utf-8")
            ).hexdigest()[:32]
            try:
                cached = await self.cache.get(cache_key_str)
                if cached:
                    return cached.strip()[:500]
            except Exception as exc:
                logger.debug("community llm cache get failed: %s", exc)

        try:
            raw = await asyncio.wait_for(
                self.llm_provider.complete(
                    prompt=prompt,
                    temperature=0.2,
                ),
                timeout=15.0,
            )
        except Exception as exc:
            logger.warning(
                "community LLM analysis failed (best-effort, analysis omitted): %s: %s",
                exc.__class__.__name__, exc,
            )
            return None

        text = (raw or "").strip()[:500]
        if not text:
            return None

        if cache_key_str is not None and self.cache is not None:
            try:
                await self.cache.set(cache_key_str, text)
            except Exception as exc:
                logger.debug("community llm cache set failed: %s", exc)
        return text

    async def _parse_git_log(
        self, repo_path: str, lookback_days: int
    ) -> tuple[float, int, list[str]]:
        # Use ASCII Unit Separator (0x1f) to avoid splitting on '|' inside commit messages.
        # `-c safe.directory=*` bypasses git 2.35+ "dubious ownership" check which
        # fires when the container runs as a different UID than the bind-mounted
        # host files (common on Docker Desktop + Windows). Scoped to this one
        # command via -c, so we don't mutate global git config.
        proc = await asyncio.create_subprocess_exec(
            "git",
            "-c",
            "safe.directory=*",
            "-C",
            repo_path,
            "log",
            "--format=%H\x1f%ae\x1f%ci",
            f"--after={lookback_days} days ago",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=40)

        if proc.returncode != 0 or (
            not stdout.strip() and b"not a git repository" in stderr.lower()
        ):
            raise _NotGitRepoError(stderr.decode("utf-8", "replace")[:200])

        emails: list[str] = []
        for line in stdout.decode("utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split("\x1f")
            if len(parts) >= 2:
                email = parts[1].strip()
                if email:
                    emails.append(email)

        total_commits = len(emails)
        unique_contributors = len(set(emails))
        top_contributors = [
            email for email, _ in Counter(emails).most_common(5)
        ]
        commits_per_week = total_commits / (lookback_days / 7.0) if lookback_days > 0 else 0.0

        return commits_per_week, unique_contributors, top_contributors

    async def _fetch_avg_issue_response(
        self, repo_path: str, github_token: str | None
    ) -> float | None:
        if not github_token:
            return None

        owner, repo = self._extract_owner_repo(repo_path)
        if not owner or not repo:
            return None

        try:
            import aiohttp  # lazy import — optional dependency

            url = f"https://api.github.com/repos/{owner}/{repo}/issues"
            headers = {
                "Authorization": f"token {github_token}",
                "Accept": "application/vnd.github.v3+json",
            }
            params = {"state": "closed", "per_page": 30}
            timeout = aiohttp.ClientTimeout(total=15)

            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers, params=params) as resp:
                    if resp.status != 200:
                        return None
                    issues = await resp.json()

            if not issues:
                return None

            total_hours = 0.0
            count = 0
            for issue in issues:
                created_at = issue.get("created_at")
                closed_at = issue.get("closed_at")
                if not created_at or not closed_at:
                    continue
                created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                closed = datetime.fromisoformat(closed_at.replace("Z", "+00:00"))
                delta_hours = (closed - created).total_seconds() / 3600.0
                total_hours += delta_hours
                count += 1

            return total_hours / count if count > 0 else None

        except Exception as exc:
            logger.warning(
                "github issues API fetch failed (best-effort, response time unknown): %s: %s",
                exc.__class__.__name__, exc,
            )
            return None

    def _extract_owner_repo(self, repo_path: str) -> tuple[str | None, str | None]:
        """Extract owner/repo from a GitHub URL or remote origin of a local repo."""
        if repo_path.startswith("https://github.com/") or repo_path.startswith(
            "git@github.com:"
        ):
            path = (
                repo_path.replace("https://github.com/", "")
                .replace("git@github.com:", "")
                .rstrip("/")
                .removesuffix(".git")
            )
            parts = path.split("/")
            if len(parts) >= 2:
                return parts[0], parts[1]
        return None, None
