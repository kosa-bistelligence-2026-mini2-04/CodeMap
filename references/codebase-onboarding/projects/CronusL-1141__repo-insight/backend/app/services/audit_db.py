from __future__ import annotations


class AuditDB:
    """SQLite-backed audit log and LLM response cache."""

    async def initialize(self, db_path: str) -> None:
        """Create tables if they do not exist."""
        raise NotImplementedError("AuditDB.initialize not implemented yet")

    async def log_job(self, job_id: str, repo: str, agents_status: dict, tokens: int) -> None:
        """Append a job record to the audit log."""
        raise NotImplementedError("AuditDB.log_job not implemented yet")

    async def get_cached_result(self, cache_key: str) -> str | None:
        """Return cached LLM result string, or None on miss."""
        raise NotImplementedError("AuditDB.get_cached_result not implemented yet")

    async def set_cached_result(self, cache_key: str, result: str, ttl_hours: int = 24) -> None:
        """Store LLM result with TTL."""
        raise NotImplementedError("AuditDB.set_cached_result not implemented yet")
