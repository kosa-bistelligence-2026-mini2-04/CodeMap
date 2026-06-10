"""Persistent storage for analysis history (SQLite via aiosqlite).

Long-term storage of every analysis run so users can:
- Browse past reports (history sidebar)
- Compare runs across time
- Recover reports after backend restart (the in-memory `_job_results` dict
  in routes.py is lost on restart)
- Aggregate cost and cache-hit statistics across runs

Schema:
    analyses — one row per submission
        job_id              TEXT PK
        source              TEXT NOT NULL   -- 'local' / 'github'
        path                TEXT NOT NULL   -- user-supplied repo identifier
        status              TEXT NOT NULL   -- 'running' / 'completed' / 'failed'
        created_at          REAL NOT NULL   -- unix timestamp, UTC
        completed_at        REAL            -- nullable
        total_pipeline_ms   INTEGER
        report_json         TEXT            -- full ReportJsonResponse as JSON
        error_message       TEXT
        model_used          TEXT
        force_refresh       INTEGER NOT NULL DEFAULT 0
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

_SCHEMA = """
CREATE TABLE IF NOT EXISTS analyses (
    job_id              TEXT PRIMARY KEY,
    source              TEXT NOT NULL,
    path                TEXT NOT NULL,
    status              TEXT NOT NULL,
    created_at          REAL NOT NULL,
    completed_at        REAL,
    total_pipeline_ms   INTEGER,
    report_json         TEXT,
    error_message       TEXT,
    model_used          TEXT,
    force_refresh       INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_analyses_created ON analyses(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_analyses_status ON analyses(status);
"""


class AnalysisStore:
    """Async SQLite-backed persistent store for analysis history."""

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        self._initialized = False

    async def _ensure_schema(self) -> None:
        if self._initialized:
            return
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            for stmt in _SCHEMA.strip().split(";"):
                s = stmt.strip()
                if s:
                    await db.execute(s)
            await db.commit()
        self._initialized = True

    async def create_running(
        self,
        job_id: str,
        source: str,
        path: str,
        model_used: str | None = None,
        force_refresh: bool = False,
    ) -> None:
        """Insert a 'running' row at submission time so the job is visible
        in history even if the backend crashes mid-pipeline."""
        await self._ensure_schema()
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """INSERT OR REPLACE INTO analyses
                   (job_id, source, path, status, created_at, model_used, force_refresh)
                   VALUES (?, ?, ?, 'running', ?, ?, ?)""",
                (job_id, source, path, time.time(), model_used, int(force_refresh)),
            )
            await db.commit()

    async def mark_completed(
        self,
        job_id: str,
        report_json: str,
        total_pipeline_ms: int,
    ) -> None:
        await self._ensure_schema()
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """UPDATE analyses
                   SET status = 'completed',
                       completed_at = ?,
                       total_pipeline_ms = ?,
                       report_json = ?
                   WHERE job_id = ?""",
                (time.time(), total_pipeline_ms, report_json, job_id),
            )
            await db.commit()

    async def mark_failed(self, job_id: str, error_message: str) -> None:
        await self._ensure_schema()
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """UPDATE analyses
                   SET status = 'failed',
                       completed_at = ?,
                       error_message = ?
                   WHERE job_id = ?""",
                (time.time(), error_message[:2000], job_id),
            )
            await db.commit()

    async def list_recent(
        self, limit: int = 50, offset: int = 0
    ) -> list[dict[str, Any]]:
        """List recent analyses (newest first). Returns lightweight summaries,
        no full report_json blob — use `get_one` for details."""
        await self._ensure_schema()
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """SELECT job_id, source, path, status, created_at, completed_at,
                          total_pipeline_ms, error_message, model_used, force_refresh
                   FROM analyses
                   ORDER BY created_at DESC
                   LIMIT ? OFFSET ?""",
                (limit, offset),
            ) as cursor:
                rows = await cursor.fetchall()

        return [
            {
                "job_id": r[0],
                "source": r[1],
                "path": r[2],
                "status": r[3],
                "created_at": r[4],
                "completed_at": r[5],
                "total_pipeline_ms": r[6],
                "error_message": r[7],
                "model_used": r[8],
                "force_refresh": bool(r[9]),
            }
            for r in rows
        ]

    async def get_one(self, job_id: str) -> dict[str, Any] | None:
        """Fetch a single analysis with full report_json blob."""
        await self._ensure_schema()
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                """SELECT job_id, source, path, status, created_at, completed_at,
                          total_pipeline_ms, report_json, error_message, model_used,
                          force_refresh
                   FROM analyses WHERE job_id = ?""",
                (job_id,),
            ) as cursor:
                r = await cursor.fetchone()

        if r is None:
            return None
        return {
            "job_id": r[0],
            "source": r[1],
            "path": r[2],
            "status": r[3],
            "created_at": r[4],
            "completed_at": r[5],
            "total_pipeline_ms": r[6],
            "report_json": r[7],
            "error_message": r[8],
            "model_used": r[9],
            "force_refresh": bool(r[10]),
        }

    async def get_report_json(self, job_id: str) -> str | None:
        """Fast path for cold-read of a completed report JSON."""
        await self._ensure_schema()
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT report_json FROM analyses WHERE job_id = ? AND status = 'completed'",
                (job_id,),
            ) as cursor:
                row = await cursor.fetchone()
        return row[0] if row else None

    async def count(self) -> int:
        await self._ensure_schema()
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM analyses") as cursor:
                row = await cursor.fetchone()
        return row[0] if row else 0

    async def delete(self, job_id: str) -> bool:
        await self._ensure_schema()
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "DELETE FROM analyses WHERE job_id = ?", (job_id,)
            )
            await db.commit()
            return cursor.rowcount > 0
