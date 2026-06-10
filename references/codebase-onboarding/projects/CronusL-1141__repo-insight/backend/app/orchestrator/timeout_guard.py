from __future__ import annotations

import hashlib
import logging
import sqlite3
import time
from pathlib import Path

from app.models.agent_schemas import CommunityResult

logger = logging.getLogger(__name__)

_CACHE_TTL_S = 86400  # 24 hours

_HISTORICAL_MEAN = CommunityResult(
    job_id="__degraded__",
    commits_per_week=3.5,
    avg_issue_response_hours=None,
    unique_contributors=2,
    top_contributors=[],
    is_degraded=True,
    degraded_reason="timeout_or_cache_miss_fallback_mean",
    duration_ms=0,
)


def _repo_hash(repo_path: str) -> str:
    return hashlib.sha256(repo_path.encode()).hexdigest()[:32]


class TimeoutGuard:
    """Handles community assessor timeout with SQLite cache + historical-mean fallback."""

    def __init__(self, db_path: str = "./data/community_cache.db") -> None:
        self._db_path = db_path
        self._initialized = False

    def _ensure_db(self) -> sqlite3.Connection:
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS community_cache (
                repo_hash TEXT PRIMARY KEY,
                commits_per_week REAL,
                avg_issue_response_hours REAL,
                unique_contributors INTEGER,
                created_at REAL
            )
            """
        )
        conn.commit()
        return conn

    async def get_degraded_community(self, job_id: str, repo_path: str) -> CommunityResult:
        """Degradation lookup (3 levels):

        Level 1: Per-repo cache hit (same repo analyzed < 24h ago) — most accurate
        Level 2: Historical mean across ALL cached runs — representative fallback
        Level 3: Hard-coded defaults (3.5/2) — only when the cache table is empty
        """
        try:
            conn = self._ensure_db()
            repo_key = _repo_hash(repo_path)
            now = time.time()

            # Level 1: per-repo cache
            row = conn.execute(
                "SELECT commits_per_week, avg_issue_response_hours, unique_contributors, created_at "
                "FROM community_cache WHERE repo_hash = ?",
                (repo_key,),
            ).fetchone()

            if row and (now - row[3]) < _CACHE_TTL_S:
                conn.close()
                return CommunityResult(
                    job_id=job_id,
                    commits_per_week=row[0] if row[0] is not None else 3.5,
                    avg_issue_response_hours=row[1],
                    unique_contributors=int(row[2]) if row[2] is not None else 2,
                    top_contributors=[],
                    is_degraded=True,
                    degraded_reason="cache_hit_within_24h",
                    duration_ms=0,
                )

            # Level 2: historical mean across all cached repos
            mean_row = conn.execute(
                "SELECT AVG(commits_per_week), AVG(unique_contributors), COUNT(*) "
                "FROM community_cache"
            ).fetchone()
            conn.close()

            if mean_row and mean_row[2] and mean_row[2] > 0:
                return CommunityResult(
                    job_id=job_id,
                    commits_per_week=float(mean_row[0] or 0.0),
                    avg_issue_response_hours=None,
                    unique_contributors=int(mean_row[1] or 0),
                    top_contributors=[],
                    is_degraded=True,
                    degraded_reason=f"historical_mean_across_{mean_row[2]}_repos",
                    duration_ms=0,
                )
        except Exception:
            logger.warning(
                "timeout_guard community_cache read failed, falling back to constant",
                exc_info=True,
            )

        # Level 3: hard-coded default when cache is empty
        return CommunityResult(
            job_id=job_id,
            commits_per_week=3.5,
            avg_issue_response_hours=None,
            unique_contributors=2,
            top_contributors=[],
            is_degraded=True,
            degraded_reason="fallback_constant_empty_cache",
            duration_ms=0,
        )

    async def cache_community_result(self, repo_path: str, result: CommunityResult) -> None:
        """Store a successful community result for future degraded fallback."""
        try:
            conn = self._ensure_db()
            repo_key = _repo_hash(repo_path)
            conn.execute(
                "INSERT OR REPLACE INTO community_cache "
                "(repo_hash, commits_per_week, avg_issue_response_hours, unique_contributors, created_at) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    repo_key,
                    result.commits_per_week,
                    result.avg_issue_response_hours,
                    result.unique_contributors,
                    time.time(),
                ),
            )
            conn.commit()
            conn.close()
        except Exception:
            logger.warning(
                "timeout_guard community_cache write failed (best-effort)",
                exc_info=True,
            )
