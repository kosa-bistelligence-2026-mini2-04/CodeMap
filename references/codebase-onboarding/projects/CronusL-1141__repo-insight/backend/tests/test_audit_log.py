from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_record_inserts_row(tmp_path):
    """AuditLogger.record() must execute a real INSERT and commit to SQLite."""
    import aiosqlite
    from app.llm.audit import AuditLogger

    db_path = str(tmp_path / "test_audit_record.db")
    logger = AuditLogger(db_path=db_path)
    await logger.record(
        agent_name="test",
        model="gpt-5.4",
        prompt_tokens=100,
        completion_tokens=50,
        cost_usd=0.001,
        cache_hit=False,
        key="abc",
    )
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("SELECT COUNT(*) FROM audit_log") as c:
            row = await c.fetchone()
    assert row[0] == 1


@pytest.mark.asyncio
async def test_audit_table_created_on_startup(tmp_path):
    """_ensure_audit_table creates llm_audit_log table when called with a fresh db."""
    import aiosqlite
    from app.llm.audit import _ensure_audit_table

    db_path = str(tmp_path / "test_audit.db")
    await _ensure_audit_table(db_path)

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='llm_audit_log'"
        )
        row = await cursor.fetchone()

    assert row is not None, "llm_audit_log table must exist after _ensure_audit_table"


@pytest.mark.asyncio
async def test_audit_table_idempotent(tmp_path):
    """Calling _ensure_audit_table twice does not raise (IF NOT EXISTS)."""
    from app.llm.audit import _ensure_audit_table

    db_path = str(tmp_path / "test_audit2.db")
    await _ensure_audit_table(db_path)
    await _ensure_audit_table(db_path)  # must not raise


@pytest.mark.asyncio
async def test_audit_record_insert(tmp_path):
    """After table creation, a row can be inserted and read back with correct fields."""
    import time
    import aiosqlite
    from app.llm.audit import _ensure_audit_table

    db_path = str(tmp_path / "test_audit3.db")
    await _ensure_audit_table(db_path)

    ts = time.time()
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "INSERT INTO llm_audit_log(timestamp, agent_name, model, prompt_tokens, completion_tokens, cost_usd, cache_hit, cache_key) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (ts, "test_agent", "gpt-5.4", 100, 50, 0.001, 0, "key-abc"),
        )
        await db.commit()

        cursor = await db.execute("SELECT agent_name, model, prompt_tokens, completion_tokens FROM llm_audit_log")
        row = await cursor.fetchone()

    assert row is not None
    assert row[0] == "test_agent"
    assert row[1] == "gpt-5.4"
    assert row[2] == 100
    assert row[3] == 50
