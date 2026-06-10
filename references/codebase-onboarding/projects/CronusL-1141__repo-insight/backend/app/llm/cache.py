from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path

_DEFAULT_DB_PATH = Path("data/llm_cache.db")
_DEFAULT_TTL_SECONDS = 24 * 3600

_hits = 0
_misses = 0


def cache_stats() -> dict[str, int]:
    return {"hits": _hits, "misses": _misses}


def reset_cache_stats() -> None:
    global _hits, _misses
    _hits = 0
    _misses = 0


def _normalize_repo_url(url: str) -> str:
    """BUG-R4 fix: normalize repo_url so cache keys are stable across runs.

    - lowercase (Windows paths / github URLs are case-insensitive)
    - replace backslashes with forward slashes
    - strip trailing slashes
    - strip .git suffix (github URLs)
    """
    if not url:
        return url
    normalized = url.strip().lower().replace("\\", "/").rstrip("/")
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    return normalized


@dataclass(frozen=True)
class CacheKey:
    repo_url: str
    agent_name: str
    file_contents_hash: str
    prompt_version: str = "v1"
    model_name: str = "gpt-5.4"
    temperature_int: int = 0

    def to_string(self) -> str:
        raw = "|".join(
            [
                _normalize_repo_url(self.repo_url),
                self.agent_name,
                self.file_contents_hash,
                self.prompt_version,
                self.model_name,
                str(self.temperature_int),
            ]
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def compute_file_contents_hash(*texts: str) -> str:
    h = hashlib.sha256()
    for t in texts:
        h.update(t.encode("utf-8"))
        h.update(b"\x00")
    return h.hexdigest()


class LLMCache:
    """Async SQLite-backed LLM response cache (aiosqlite)."""

    _SCHEMA = (
        "CREATE TABLE IF NOT EXISTS llm_cache ("
        "  key TEXT PRIMARY KEY,"
        "  value TEXT NOT NULL,"
        "  created_at REAL NOT NULL,"
        "  ttl REAL NOT NULL"
        ")"
    )

    def __init__(self, db_path: str | Path = _DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self._initialized = False

    async def _ensure_schema(self) -> None:
        if self._initialized:
            return
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(self._SCHEMA)
            await db.commit()
        self._initialized = True

    async def get(self, key: str) -> str | None:
        global _hits, _misses
        await self._ensure_schema()
        import aiosqlite

        now = time.time()
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                "SELECT value, created_at, ttl FROM llm_cache WHERE key = ?",
                (key,),
            ) as cursor:
                row = await cursor.fetchone()
        if row is None:
            _misses += 1
            return None
        value, created_at, ttl = row
        if created_at + ttl <= now:
            _misses += 1
            return None
        _hits += 1
        return value

    async def set(
        self,
        key: str,
        value: str,
        ttl: float = _DEFAULT_TTL_SECONDS,
    ) -> None:
        await self._ensure_schema()
        import aiosqlite

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO llm_cache(key, value, created_at, ttl)"
                " VALUES (?, ?, ?, ?)",
                (key, value, time.time(), float(ttl)),
            )
            await db.commit()
