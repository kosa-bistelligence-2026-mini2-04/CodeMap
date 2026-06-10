"""Unit tests for the persistent analysis history store."""
from __future__ import annotations

import json

import pytest

from app.services.analysis_store import AnalysisStore


@pytest.mark.asyncio
async def test_create_running_persists_row(tmp_path):
    store = AnalysisStore(db_path=tmp_path / "analyses.db")
    await store.create_running(
        job_id="job-1",
        source="local",
        path="/tmp/repo",
        model_used="gpt-5.4",
        force_refresh=False,
    )
    row = await store.get_one("job-1")
    assert row is not None
    assert row["status"] == "running"
    assert row["source"] == "local"
    assert row["path"] == "/tmp/repo"
    assert row["model_used"] == "gpt-5.4"
    assert row["completed_at"] is None


@pytest.mark.asyncio
async def test_mark_completed_stores_full_report_blob(tmp_path):
    store = AnalysisStore(db_path=tmp_path / "analyses.db")
    await store.create_running(
        job_id="job-2", source="github", path="https://github.com/x/y"
    )

    payload = {
        "job_id": "job-2",
        "status": "completed",
        "recommendations": [],
        "community": {"commits_per_week": 1.0},
    }
    await store.mark_completed(
        job_id="job-2",
        report_json=json.dumps(payload),
        total_pipeline_ms=12345,
    )

    row = await store.get_one("job-2")
    assert row["status"] == "completed"
    assert row["total_pipeline_ms"] == 12345
    assert row["completed_at"] is not None

    blob = await store.get_report_json("job-2")
    assert blob is not None
    parsed = json.loads(blob)
    assert parsed["job_id"] == "job-2"


@pytest.mark.asyncio
async def test_mark_failed_records_error_message(tmp_path):
    store = AnalysisStore(db_path=tmp_path / "analyses.db")
    await store.create_running(job_id="job-3", source="local", path="/bad")
    await store.mark_failed("job-3", "RuntimeError: boom")

    row = await store.get_one("job-3")
    assert row["status"] == "failed"
    assert "boom" in (row["error_message"] or "")
    # Failed runs should NOT return a report_json via fast path
    blob = await store.get_report_json("job-3")
    assert blob is None


@pytest.mark.asyncio
async def test_list_recent_newest_first(tmp_path):
    store = AnalysisStore(db_path=tmp_path / "analyses.db")
    for i in range(5):
        await store.create_running(
            job_id=f"job-{i}", source="local", path=f"/repo-{i}"
        )

    rows = await store.list_recent(limit=10)
    # Newest first (highest created_at)
    assert len(rows) == 5
    assert rows[0]["job_id"] == "job-4"
    assert rows[-1]["job_id"] == "job-0"

    # pagination
    page1 = await store.list_recent(limit=2, offset=0)
    page2 = await store.list_recent(limit=2, offset=2)
    assert page1[0]["job_id"] == "job-4"
    assert page1[1]["job_id"] == "job-3"
    assert page2[0]["job_id"] == "job-2"


@pytest.mark.asyncio
async def test_count_and_delete(tmp_path):
    store = AnalysisStore(db_path=tmp_path / "analyses.db")
    await store.create_running(job_id="a", source="local", path="/a")
    await store.create_running(job_id="b", source="local", path="/b")
    assert await store.count() == 2

    assert await store.delete("a") is True
    assert await store.count() == 1
    assert await store.delete("nonexistent") is False


@pytest.mark.asyncio
async def test_get_one_returns_none_for_missing(tmp_path):
    store = AnalysisStore(db_path=tmp_path / "analyses.db")
    assert await store.get_one("nope") is None


@pytest.mark.asyncio
async def test_create_running_replaces_on_same_job_id(tmp_path):
    store = AnalysisStore(db_path=tmp_path / "analyses.db")
    await store.create_running(job_id="same", source="local", path="/first")
    await store.create_running(job_id="same", source="github", path="/second")
    row = await store.get_one("same")
    assert row["source"] == "github"
    assert row["path"] == "/second"
    assert await store.count() == 1
