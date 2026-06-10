from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router, _job_results
from app.api.progress_bus import ProgressBus
from app.models.api_schemas import CommunityMetrics, GuardrailTelemetry, ReportJsonResponse
from app.services.observability import ObservabilityCollector


# ---------------------------------------------------------------------------
# App factory for tests
# ---------------------------------------------------------------------------

def _make_test_app(planner=None, bus=None, observability=None, store=None) -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    mock_planner = planner or AsyncMock()
    mock_bus = bus or ProgressBus()
    mock_obs = observability or ObservabilityCollector()

    # AnalysisStore mock with no-op persistence methods so routes don't crash
    if store is None:
        store = AsyncMock()
        store.create_running = AsyncMock(return_value=None)
        store.mark_completed = AsyncMock(return_value=None)
        store.mark_failed = AsyncMock(return_value=None)
        store.get_report_json = AsyncMock(return_value=None)
        store.get_one = AsyncMock(return_value=None)
        store.list_recent = AsyncMock(return_value=[])
        store.count = AsyncMock(return_value=0)
        store.delete = AsyncMock(return_value=False)

    app.state.planner = mock_planner
    app.state.progress_bus = mock_bus
    app.state.observability = mock_obs
    app.state.analysis_store = store
    return app


def _make_report(job_id="test-job") -> ReportJsonResponse:
    return ReportJsonResponse(
        job_id=job_id,
        status="completed",
        completed_at=datetime.now(timezone.utc),
        total_pipeline_ms=500,
        recommendations=[],
        community=CommunityMetrics(commits_per_week=3.0, unique_contributors=2),
        html_report="<html>report</html>",
        guardrail_telemetry=None,
    )


# ---------------------------------------------------------------------------
# T6 Test 1: POST /api/analyze returns job_id + ws_url
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_analyze_returns_job_id_and_ws_url():
    app = _make_test_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/analyze",
            json={"source": "local", "path": "/home/user/myrepo"},
        )
    assert resp.status_code == 202
    data = resp.json()
    assert "job_id" in data
    assert "ws_url" in data
    assert data["ws_url"].startswith("/ws/progress/")


# ---------------------------------------------------------------------------
# T6 Test 2: POST /api/analyze with invalid source returns 422
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_analyze_invalid_source_returns_422():
    app = _make_test_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/analyze",
            json={"source": "ftp", "path": "ftp://example.com/repo"},
        )
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# T6 Test 3: GET /api/report/{job_id}?format=json returns ReportJsonResponse
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_report_json_returns_report():
    job_id = "completed-job-123"
    report = _make_report(job_id=job_id)
    _job_results[job_id] = report

    app = _make_test_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/report/{job_id}?format=json")

    del _job_results[job_id]
    assert resp.status_code == 200
    data = resp.json()
    assert data["job_id"] == job_id
    assert data["status"] == "completed"


# ---------------------------------------------------------------------------
# T6 Test 4: GET /metrics returns Prometheus format with core metrics
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_metrics_returns_prometheus_format():
    obs = ObservabilityCollector()
    obs.record_pipeline(
        job_id="j1",
        duration_ms=5000,
        stage_durations={},
        guardrail_telemetry=GuardrailTelemetry(),
        recommendation_count=3,
    )
    app = _make_test_app(observability=obs)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text
    assert "repoinsight_pipeline_duration_seconds" in body
    assert "repoinsight_fallback_triggered_total" in body
    assert "repoinsight_cache_hit_rate" in body
