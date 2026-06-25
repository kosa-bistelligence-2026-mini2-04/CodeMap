import json
import logging
import uuid
import time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.repository import ChatRepository
from app.chat.run_registry import run_registry
from app.chat.schemas import ChatRunRequest
from app.chat.service import RepositoryChatService
from app.infra.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Repository Chat"])


def _event(payload: dict) -> str:
    event_type = payload.get("type", "message")
    data = json.dumps(payload, ensure_ascii=False)
    return f"event: {event_type}\ndata: {data}\n\n"


def _references_from_worker_results(worker_results: list[dict]) -> list[dict]:
    references: list[dict] = []
    seen: set[tuple[str, int]] = set()
    for result in worker_results:
        file_path = result.get("path")
        if not file_path:
            continue
        line_start = result.get("lineStart")
        line = line_start if line_start is not None else 1
        key = (str(file_path), int(line))
        if key in seen:
            continue
        seen.add(key)
        references.append({
            "file": str(file_path),
            "line": int(line),
            "snippet": str(result.get("snippet", ""))[:240],
        })
    return references


def _cancelled_event(run_id: str, record) -> dict:
    return {"type": "cancelled", "runId": run_id, "cancelledAt": record.completed_at_iso}


async def _replay_stream(record):
    """Replay known events for reconnects without starting a second graph run."""
    for event in record.events:
        yield _event(event)
    if not record.is_terminal:
        yield _event({"type": "run_reconnect", "runId": record.run_id, "status": record.status})


@router.post("/{repo_id}/runs", status_code=202)
async def create_chat_run(repo_id: UUID, request: ChatRunRequest, db: AsyncSession = Depends(get_db)):
    """
    LangGraph 멀티에이전트 실행 생성 엔드포인트.
    """
    service = RepositoryChatService(db)
    try:
        job, mode, clone_path = await service.prepare_run_context(repo_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=409 if "준비" in str(exc) else 404, detail=str(exc)) from exc

    run_id = str(uuid.uuid4())
    session_id = request.sessionId or uuid.uuid4()
    prepared_request = request.model_copy(update={"sessionId": session_id})
    run_registry.create(
        run_id=run_id,
        repo_id=repo_id,
        session_id=str(session_id),
        request=prepared_request,
        job=job,
        clone_path=clone_path,
        mode=mode,
    )

    return {
        "code": 202,
        "message": "accepted",
        "data": {
            "runId": run_id,
            "sessionId": str(session_id),
            "status": "queued",
            "streamUrl": f"/api/chat/{repo_id}/runs/{run_id}/stream",
            "statusUrl": f"/api/chat/{repo_id}/runs/{run_id}",
            "evidenceUrl": f"/api/chat/{repo_id}/runs/{run_id}/evidence"
        }
    }


@router.get("/{repo_id}/runs/{run_id}/stream")
async def stream_chat_run(repo_id: UUID, run_id: str, db: AsyncSession = Depends(get_db)):
    """
    LangGraph 멀티에이전트 SSE 스트리밍.
    """
    record = run_registry.get(run_id)
    if not record or record.repo_id != repo_id:
        raise HTTPException(status_code=404, detail="Run not found")
    if not await record.claim_for_stream():
        return StreamingResponse(
            _replay_stream(record),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    request: ChatRunRequest = record.request
    clone_path = record.clone_path
    job = record.job
    mode = record.mode
    service = RepositoryChatService(db)

    async def stream():
        thread = None
        try:
            _, thread, _, _ = await service.prepare(
                repo_id,
                request,
                commit_user_message=False,
            )
            graph_started_event = {"type": "graph_started", "runId": run_id, "stateKeys": ["user_query"]}
            record.events.append(graph_started_event)
            yield _event(graph_started_event)

            # Graph Stream
            async for event in service.run_agent_stream(repo_id, request.question, clone_path, run_id):
                if record.cancel_event.is_set():
                    await record.mark_cancelled()
                    cancelled_event = _cancelled_event(run_id, record)
                    if not record.events or record.events[-1] != cancelled_event:
                        record.events.append(cancelled_event)
                    yield _event(cancelled_event)
                    await db.rollback()
                    return

                if event.get("type") == "internal_state":
                    record.compact_context = event["compact_context"]
                    record.worker_results = event["worker_results"]
                    continue
                record.events.append(event)
                record.current_node = event.get("type")
                yield _event(event)

            if record.cancel_event.is_set():
                await record.mark_cancelled()
                cancelled_event = _cancelled_event(run_id, record)
                record.events.append(cancelled_event)
                yield _event(cancelled_event)
                await db.rollback()
                return

            record.status = "streaming"
            record.current_node = "answer_delta"
            # Final Answer Agent Stream
            async for event in service.stream_answer(
                repo_name=job.repo_name,
                user_query=request.question,
                compact_context=record.compact_context,
                worker_results=record.worker_results,
                mode=mode,
            ):
                if record.cancel_event.is_set():
                    await record.mark_cancelled()
                    cancelled_event = _cancelled_event(run_id, record)
                    if not record.events or record.events[-1] != cancelled_event:
                        record.events.append(cancelled_event)
                    yield _event(cancelled_event)
                    await db.rollback()
                    return

                if event.get("type") == "answer_delta":
                    record.accumulated_answer += event.get("content", "")
                record.events.append(event)
                yield _event(event)

            if record.cancel_event.is_set():
                await record.mark_cancelled()
                cancelled_event = _cancelled_event(run_id, record)
                record.events.append(cancelled_event)
                yield _event(cancelled_event)
                await db.rollback()
                return

            # DB 저장과 completed 전이를 같은 terminal lock 경계에서 처리한다.
            async with record.transition_lock:
                if record.is_terminal or record.cancel_event.is_set():
                    cancelled_event = _cancelled_event(run_id, record)
                    record.events.append(cancelled_event)
                    yield _event(cancelled_event)
                    await db.rollback()
                    return
                await service.persist_answer(thread, record.accumulated_answer, mode, record.worker_results)
                record.status = "completed"
                record.current_node = None
                record.completed_at = time.time()

            # References
            record.references = _references_from_worker_results(record.worker_results)
            if record.references:
                references_event = {"type": "references", "references": record.references}
                record.events.append(references_event)
                yield _event(references_event)

            completed_event = {"type": "completed", "runId": run_id, "status": "completed"}
            record.events.append(completed_event)
            yield _event(completed_event)

        except Exception as exc:
            logger.exception("[ChatRouter] SSE stream 오류 run=%s", run_id)
            await record.mark_failed(str(exc))
            failed_event = {"type": "failed", "runId": run_id, "error": str(exc)}
            record.events.append(failed_event)
            yield _event(failed_event)
            await db.rollback()

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/{repo_id}/threads")
async def list_threads(repo_id: UUID, db: AsyncSession = Depends(get_db)):
    threads = await ChatRepository(db).list_threads(repo_id)
    return {"items": [{
        "id": str(item.id), "repoId": str(item.repo_id), "title": item.title,
        "createdAt": item.created_at.isoformat(), "updatedAt": item.updated_at.isoformat(),
    } for item in threads]}


@router.get("/{repo_id}/threads/{thread_id}")
async def get_thread(repo_id: UUID, thread_id: UUID, db: AsyncSession = Depends(get_db)):
    messages = await ChatRepository(db).list_messages(repo_id, thread_id)
    return {"items": [{
        "id": str(item.id), "role": item.role, "content": item.content, "mode": item.mode,
        "references": item.references, "createdAt": item.created_at.isoformat(),
    } for item in messages]}
