from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect, status
from fastapi.responses import HTMLResponse, PlainTextResponse

from app.models.api_schemas import AnalyzeRequest, AnalyzeResponse, ReportJsonResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Router layout
# ---------------------------------------------------------------------------
# Three sub-routers are composed into one public `router` so main.py continues
# to just `include_router(router)` and URL paths stay IDENTICAL to before:
#
#   api_router      — prefix="/api"   (all application endpoints)
#   ws_router       — no prefix        (WebSocket progress stream)
#   metrics_router  — no prefix        (Prometheus /metrics lives at root by
#                                       Prometheus convention, not under /api)
# ---------------------------------------------------------------------------

api_router = APIRouter(prefix="/api", tags=["api"])
ws_router = APIRouter()
metrics_router = APIRouter()

# In-memory job store: job_id -> ReportJsonResponse | Exception | None (None=running)
_job_results: dict[str, ReportJsonResponse | Exception | None] = {}


def _get_planner(request: Request):
    return request.app.state.planner


def _get_bus(request: Request):
    return request.app.state.progress_bus


def _get_observability(request: Request):
    return request.app.state.observability


def _get_store(request: Request):
    return request.app.state.analysis_store


@api_router.post(
    "/analyze",
    response_model=AnalyzeResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["analyze"],
)
async def submit_analysis(
    payload: AnalyzeRequest,
    planner=Depends(_get_planner),
    bus=Depends(_get_bus),
    store=Depends(_get_store),
) -> AnalyzeResponse:
    """Submit a repository for analysis. Returns job_id immediately; runs async."""
    job_id = str(uuid.uuid4())
    _job_results[job_id] = None

    # Record the 'running' row up front so it's visible in history even if
    # the backend crashes or the pipeline fails hard. All persist/publish
    # calls below are best-effort — any failure is logged but never blocks
    # the pipeline (users care about the report, not the audit trail).
    try:
        await store.create_running(
            job_id=job_id,
            source=payload.source,
            path=payload.path,
            model_used=None,  # filled on completion via report blob
            force_refresh=payload.force_refresh,
        )
    except Exception as exc:
        logger.warning(
            "analysis_store.create_running failed (best-effort): %s: %s",
            exc.__class__.__name__, exc,
        )

    async def _run():
        try:
            result = await planner.run_pipeline(
                job_id,
                payload.source,
                payload.path,
                payload.force_refresh,
                payload.model,
            )
            _job_results[job_id] = result
            # Persist the completed report so it survives restarts and shows
            # up in the history sidebar.
            try:
                blob = result.model_dump_json()
                await store.mark_completed(
                    job_id=job_id,
                    report_json=blob,
                    total_pipeline_ms=getattr(result, "total_pipeline_ms", 0),
                )
            except Exception as exc:
                logger.warning(
                    "analysis_store.mark_completed failed (best-effort): %s: %s",
                    exc.__class__.__name__, exc,
                )
            try:
                await bus.publish(job_id, {
                    "type": "completed",
                    "job_id": job_id,
                    "total_pipeline_ms": getattr(result, "total_pipeline_ms", 0),
                })
            except Exception as exc:
                logger.warning(
                    "progress_bus publish completed failed (best-effort): %s: %s",
                    exc.__class__.__name__, exc,
                )
        except Exception as exc:
            _job_results[job_id] = exc
            logger.exception("pipeline raised unhandled exception for job %s", job_id)
            try:
                await store.mark_failed(job_id, f"{type(exc).__name__}: {exc}")
            except Exception as store_exc:
                logger.warning(
                    "analysis_store.mark_failed failed (best-effort): %s: %s",
                    store_exc.__class__.__name__, store_exc,
                )
            try:
                await bus.publish(job_id, {
                    "type": "failed",
                    "job_id": job_id,
                    "error_code": type(exc).__name__,
                    "message": str(exc)[:500],
                })
            except Exception as pub_exc:
                logger.warning(
                    "progress_bus publish failed event dropped (best-effort): %s: %s",
                    pub_exc.__class__.__name__, pub_exc,
                )

    asyncio.create_task(_run())

    return AnalyzeResponse(
        job_id=job_id,
        status="queued",
        created_at=datetime.now(timezone.utc),
        ws_url=f"/ws/progress/{job_id}",
    )


@api_router.get("/report/{job_id}", tags=["report"], response_model=None)
async def get_report(
    job_id: str,
    format: str = "html",
    store=Depends(_get_store),
):
    """Retrieve the completed analysis report.

    Lookup order: in-memory _job_results -> persistent AnalysisStore.
    This makes reports survive backend restarts and lets the history
    sidebar load any past run.
    """
    result = _job_results.get(job_id)

    # Cold-read fallback: if not in memory, try the persistent store.
    if result is None and job_id not in _job_results:
        blob = await store.get_report_json(job_id)
        if blob is None:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
        try:
            cached = ReportJsonResponse.model_validate_json(blob)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"Corrupt stored report: {exc}")
        if format == "json":
            return cached
        html = cached.html_report or "<p>No HTML report generated.</p>"
        return HTMLResponse(content=html)

    if result is None:
        raise HTTPException(status_code=202, detail="Job still running")
    if isinstance(result, Exception):
        raise HTTPException(status_code=500, detail=str(result))

    if format == "json":
        return result  # FastAPI serializes Pydantic model

    html = result.html_report or "<p>No HTML report generated.</p>"
    return HTMLResponse(content=html)


@api_router.get("/models", tags=["models"])
async def list_models() -> dict:
    """Return the LLM model catalog for the currently configured provider.

    Frontend uses this to populate the model dropdown so users only see
    models that actually work against the backend's configured OPENAI_BASE_URL.
    Supported providers: OpenAI / DeepSeek / Qwen / Zhipu / Moonshot / Custom.
    """
    from app.services.provider_catalog import catalog_to_dict, detect_provider
    return catalog_to_dict(detect_provider())


@api_router.get("/analyses", tags=["history"])
async def list_analyses(
    limit: int = 50,
    offset: int = 0,
    store=Depends(_get_store),
) -> dict:
    """List recent analyses newest-first for the history sidebar."""
    items = await store.list_recent(limit=min(limit, 200), offset=max(offset, 0))
    total = await store.count()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@api_router.get("/analyses/{job_id}", tags=["history"])
async def get_analysis_detail(
    job_id: str,
    store=Depends(_get_store),
) -> dict:
    """Fetch a single analysis with full report JSON from persistent store."""
    row = await store.get_one(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Analysis {job_id} not found")
    return row


@api_router.delete("/analyses/{job_id}", tags=["history"])
async def delete_analysis(
    job_id: str,
    store=Depends(_get_store),
) -> dict:
    deleted = await store.delete(job_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Analysis {job_id} not found")
    return {"deleted": job_id}


@api_router.get("/health", tags=["health"])
async def health_check() -> dict:
    return {
        "status": "ok",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "dependencies": {
            "sqlite": "ok",
            "llm_provider": "ok",
        },
    }


@metrics_router.get("/metrics", tags=["observability"], response_class=PlainTextResponse)
async def get_metrics(observability=Depends(_get_observability)) -> str:
    """Prometheus-format metrics endpoint (lives at root per Prometheus convention)."""
    return observability.prometheus_format()


_STAGE_TO_AGENT = {
    "reporter": "reporter",
    # clone / analysis / guardrail have no direct agent tile; pass through as raw stage
}


@ws_router.websocket("/ws/progress/{job_id}")
async def ws_progress(websocket: WebSocket, job_id: str) -> None:
    """Subscribe to real-time progress events for a job via WebSocket.

    U-1 fix: translates planner `stage` events whose stage maps to a known
    frontend agent tile into `agent_status` events so the ProgressPanel
    updates in real time. Other events pass through unchanged.
    """
    await websocket.accept()
    try:
        bus = websocket.app.state.progress_bus
        async for event in bus.subscribe(job_id, timeout=300.0):
            ts = datetime.now(timezone.utc).isoformat()

            if event.get("type") == "stage":
                agent = _STAGE_TO_AGENT.get(event.get("stage", ""))
                if agent is not None:
                    stage_status = event.get("status", "running")
                    payload = {
                        "type": "agent_status",
                        "job_id": job_id,
                        "timestamp": ts,
                        "agent": agent,
                        "status": stage_status,
                        "progress": 100 if stage_status == "completed" else 0,
                    }
                else:
                    payload = {"job_id": job_id, "timestamp": ts, **event}
            else:
                payload = {"job_id": job_id, "timestamp": ts, **event}

            await websocket.send_text(json.dumps(payload, default=str))
            if event.get("type") == "completed":
                break

        result = _job_results.get(job_id)
        if isinstance(result, ReportJsonResponse):
            await websocket.send_text(json.dumps({
                "type": "completed",
                "job_id": job_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "report_url": f"/api/report/{job_id}",
                "total_pipeline_ms": result.total_pipeline_ms,
            }))

    except WebSocketDisconnect:
        pass
    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Public composite router — what main.py imports.
# URL paths remain identical to the pre-refactor layout.
# ---------------------------------------------------------------------------
router = APIRouter()
router.include_router(api_router)
router.include_router(ws_router)
router.include_router(metrics_router)
