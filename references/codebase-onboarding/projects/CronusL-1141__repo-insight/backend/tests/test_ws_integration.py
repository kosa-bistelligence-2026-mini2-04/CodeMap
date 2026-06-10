"""Integration tests for the WebSocket progress bridge.

These tests are the canonical contract between backend pipeline events and
frontend ProgressPanel / useAnalysisJob. They exist specifically to catch
regressions in the WS stream (idle-timeout bug, missing terminal event,
stage->agent translation) that unit tests miss.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.progress_bus import ProgressBus
from app.api.routes import router, _job_results
from app.models.agent_schemas import CommunityResult
from app.models.api_schemas import CommunityMetrics, ReportJsonResponse
from app.services.observability import ObservabilityCollector


def _make_app(planner) -> FastAPI:
    app = FastAPI()
    app.include_router(router)
    app.state.planner = planner
    app.state.progress_bus = ProgressBus()
    app.state.observability = ObservabilityCollector()
    store = AsyncMock()
    store.create_running = AsyncMock(return_value=None)
    store.mark_completed = AsyncMock(return_value=None)
    store.mark_failed = AsyncMock(return_value=None)
    store.get_report_json = AsyncMock(return_value=None)
    store.get_one = AsyncMock(return_value=None)
    store.list_recent = AsyncMock(return_value=[])
    store.count = AsyncMock(return_value=0)
    store.delete = AsyncMock(return_value=False)
    app.state.analysis_store = store
    return app


def _make_report(job_id: str) -> ReportJsonResponse:
    return ReportJsonResponse(
        job_id=job_id,
        status="completed",
        completed_at=datetime.now(timezone.utc),
        total_pipeline_ms=1234,
        recommendations=[],
        community=CommunityMetrics(commits_per_week=1.0, unique_contributors=1),
        agent_durations={
            "static_analyzer": 300,
            "behavior_inferer": 500,
            "community_assessor": 200,
            "reporter": 234,
        },
    )


# ---------------------------------------------------------------------------
# 1. Happy path: WS receives the full event sequence and a terminal event
# ---------------------------------------------------------------------------


def test_ws_receives_agent_status_events_and_completed():
    """Full happy-path flow: POST /api/analyze -> WS gets agent_status events
    during the pipeline + a 'completed' terminal event."""
    received_events: list[dict] = []

    async def fake_run_pipeline(job_id: str, source: str, path: str, force_refresh: bool = False, model_override: str | None = None):
        bus: ProgressBus = app.state.progress_bus
        # Mimic what the real planner emits
        for agent in ("static_analyzer", "behavior_inferer", "community_assessor"):
            await bus.publish(job_id, {
                "type": "agent_status",
                "agent": agent,
                "status": "running",
                "progress": 10,
            })
        await asyncio.sleep(0.05)
        for agent in ("static_analyzer", "behavior_inferer", "community_assessor"):
            await bus.publish(job_id, {
                "type": "agent_status",
                "agent": agent,
                "status": "completed",
                "progress": 100,
            })
        await bus.publish(job_id, {
            "type": "stage",
            "stage": "reporter",
            "status": "running",
        })
        await bus.publish(job_id, {
            "type": "stage",
            "stage": "reporter",
            "status": "completed",
        })
        return _make_report(job_id)

    planner = AsyncMock()
    planner.run_pipeline.side_effect = fake_run_pipeline

    app = _make_app(planner)

    with TestClient(app) as client:
        resp = client.post("/api/analyze", json={"source": "local", "path": "/tmp/fake"})
        assert resp.status_code == 202
        job_id = resp.json()["job_id"]

        with client.websocket_connect(f"/ws/progress/{job_id}") as ws:
            while True:
                try:
                    event = ws.receive_json(mode="text")
                except Exception:
                    break
                received_events.append(event)
                if event.get("type") in ("completed", "failed"):
                    break

        _job_results.pop(job_id, None)

    # Assert we received: 3 running agent_status, 3 completed agent_status,
    # 2 translated reporter stage->agent_status, and a terminal completed.
    agent_status_events = [e for e in received_events if e.get("type") == "agent_status"]
    # At least the 3 running + 3 completed + 2 reporter stage→agent
    assert len(agent_status_events) >= 8, (
        f"expected ≥8 agent_status events, got {len(agent_status_events)}: {agent_status_events}"
    )

    running_agents = {
        e["agent"] for e in agent_status_events
        if e.get("status") == "running" and e["agent"] != "reporter"
    }
    assert running_agents == {"static_analyzer", "behavior_inferer", "community_assessor"}

    # Stage reporter was translated to agent=reporter
    reporter_events = [e for e in agent_status_events if e.get("agent") == "reporter"]
    assert any(e.get("status") == "running" for e in reporter_events)
    assert any(e.get("status") == "completed" for e in reporter_events)

    # Terminal completed event must be present
    assert any(e.get("type") == "completed" for e in received_events)


# ---------------------------------------------------------------------------
# 2. WS survives a 6-second event silence (>5s bus poll timeout)
# ---------------------------------------------------------------------------


def test_ws_stream_survives_long_idle_between_events():
    """Regression: bus.subscribe() used to break on 5s idle, killing the WS
    stream while agents were still running. Now the 5s tick is just a
    cancellation checkpoint and the stream stays alive until the overall
    deadline or a terminal event."""
    received_types: list[str] = []

    async def fake_run_pipeline(job_id: str, source: str, path: str, force_refresh: bool = False, model_override: str | None = None):
        bus: ProgressBus = app.state.progress_bus
        await bus.publish(job_id, {
            "type": "agent_status",
            "agent": "static_analyzer",
            "status": "running",
            "progress": 10,
        })
        # Simulate a real agent doing work with no event emission for 6 seconds
        await asyncio.sleep(6.0)
        await bus.publish(job_id, {
            "type": "agent_status",
            "agent": "static_analyzer",
            "status": "completed",
            "progress": 100,
        })
        return _make_report(job_id)

    planner = AsyncMock()
    planner.run_pipeline.side_effect = fake_run_pipeline

    app = _make_app(planner)

    with TestClient(app) as client:
        resp = client.post("/api/analyze", json={"source": "local", "path": "/tmp/fake"})
        job_id = resp.json()["job_id"]

        with client.websocket_connect(f"/ws/progress/{job_id}") as ws:
            while True:
                try:
                    event = ws.receive_json(mode="text")
                except Exception:
                    break
                received_types.append(event.get("type"))
                if event.get("type") in ("completed", "failed"):
                    break

        _job_results.pop(job_id, None)

    # Must have received BOTH the pre-idle running event AND the post-idle completed
    assert "agent_status" in received_types
    assert received_types.count("agent_status") >= 2, (
        f"expected at least 2 agent_status events across the 6s idle, got: {received_types}"
    )
    assert "completed" in received_types


# ---------------------------------------------------------------------------
# 3. Pipeline exception -> WS receives a 'failed' terminal event
# ---------------------------------------------------------------------------


def test_ws_receives_failed_event_on_pipeline_exception():
    """When planner.run_pipeline raises, the WS bridge should publish a
    terminal 'failed' event instead of making the frontend hang."""
    received_types: list[str] = []

    async def fake_run_pipeline(job_id: str, source: str, path: str, force_refresh: bool = False, model_override: str | None = None):
        raise RuntimeError("boom")

    planner = AsyncMock()
    planner.run_pipeline.side_effect = fake_run_pipeline

    app = _make_app(planner)

    with TestClient(app) as client:
        resp = client.post("/api/analyze", json={"source": "local", "path": "/tmp/fake"})
        job_id = resp.json()["job_id"]

        with client.websocket_connect(f"/ws/progress/{job_id}") as ws:
            while True:
                try:
                    event = ws.receive_json(mode="text")
                except Exception:
                    break
                received_types.append(event.get("type"))
                if event.get("type") in ("completed", "failed"):
                    break

        _job_results.pop(job_id, None)

    assert "failed" in received_types


# ---------------------------------------------------------------------------
# 4. Stage events that don't map to an agent pass through unchanged
# ---------------------------------------------------------------------------


def test_ws_non_translated_stage_event_passthrough():
    """Non-reporter stage events should pass through unchanged so the
    frontend can render global banners (clone/analysis/guardrail)."""
    received: list[dict] = []

    async def fake_run_pipeline(job_id: str, source: str, path: str, force_refresh: bool = False, model_override: str | None = None):
        bus: ProgressBus = app.state.progress_bus
        await bus.publish(job_id, {
            "type": "stage",
            "stage": "clone",
            "status": "running",
        })
        await bus.publish(job_id, {
            "type": "stage",
            "stage": "clone",
            "status": "completed",
        })
        return _make_report(job_id)

    planner = AsyncMock()
    planner.run_pipeline.side_effect = fake_run_pipeline

    app = _make_app(planner)

    with TestClient(app) as client:
        resp = client.post("/api/analyze", json={"source": "local", "path": "/tmp/fake"})
        job_id = resp.json()["job_id"]

        with client.websocket_connect(f"/ws/progress/{job_id}") as ws:
            while True:
                try:
                    event = ws.receive_json(mode="text")
                except Exception:
                    break
                received.append(event)
                if event.get("type") in ("completed", "failed"):
                    break

        _job_results.pop(job_id, None)

    stage_events = [e for e in received if e.get("type") == "stage"]
    assert any(e.get("stage") == "clone" and e.get("status") == "running" for e in stage_events)
    assert any(e.get("stage") == "clone" and e.get("status") == "completed" for e in stage_events)
