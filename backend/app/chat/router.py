import json
import logging
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.repository import ChatRepository
from app.chat.schemas import ChatLegacyRequest, ChatRunRequest
from app.chat.service import RepositoryChatService
from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Repository Chat"])

# 임시 메모리 저장소 (DB 모델 대신 API 명세 맞춤용)
_RUN_STORE: dict[str, dict] = {}


def _event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _references_from_worker_results(worker_results: list[dict]) -> list[dict]:
    references: list[dict] = []
    seen: set[tuple[str, int]] = set()
    for result in worker_results:
        file_path = result.get("path")
        if not file_path:
            continue
        line = result.get("lineStart") or 1
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


def _legacy_graph_event_payload(event: dict) -> dict | None:
    event_type = event.get("type")
    if event_type == "graph_started":
        return {"type": "status", "phase": "searching"}
    if event_type == "route_validated":
        groups = event.get("parallelGroups") or []
        return {"type": "exploration", "step": f"에이전트 작업 {len(groups)}개를 검증했습니다."}
    if event_type == "worker_result":
        worker = event.get("worker", "worker")
        count = event.get("resultCount", 0)
        return {"type": "exploration", "step": f"{worker} worker가 근거 {count}개를 수집했습니다."}
    if event_type == "evidence_compacted":
        return {"type": "status", "phase": "building_context"}
    if event_type == "answer_delta":
        return {"type": "content", "content": event.get("content", "")}
    if event_type == "failed":
        return {"type": "error", "error": event.get("error", "응답을 생성하지 못했습니다.")}
    return None


@router.post("/{repo_id}/runs", status_code=202)
async def create_chat_run(repo_id: UUID, request: ChatRunRequest, db: AsyncSession = Depends(get_db)):
    """
    LangGraph 멀티에이전트 실행 생성 엔드포인트.
    """
    service = RepositoryChatService(db)
    try:
        job, thread, mode, clone_path = await service.prepare(repo_id, request)
    except ValueError as exc:
        raise HTTPException(status_code=409 if "준비" in str(exc) else 404, detail=str(exc)) from exc

    run_id = str(uuid.uuid4())
    _RUN_STORE[run_id] = {
        "repo_id": repo_id,
        "request": request,
        "thread": thread,
        "job": job,
        "clone_path": clone_path,
        "mode": mode
    }

    base_url = f"/api/chat/{repo_id}/runs/{run_id}"
    return {
        "code": 202,
        "message": "accepted",
        "data": {
            "runId": run_id,
            "sessionId": str(thread.id),
            "status": "queued",
            "streamUrl": f"{base_url}/stream",
            "statusUrl": base_url,
            "evidenceUrl": f"{base_url}/evidence"
        }
    }


@router.post("/{repo_id}")
async def chat_legacy_endpoint(
    repo_id: UUID,
    request: ChatLegacyRequest,
    db: AsyncSession = Depends(get_db),
):
    """기존 단일 API 규격을 유지하기 위한 하위 호환성 SSE 브릿지."""
    service = RepositoryChatService(db)
    run_request = request.to_run_request()
    try:
        job, thread, mode, clone_path = await service.prepare(
            repo_id,
            run_request,
            commit_user_message=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409 if "준비" in str(exc) else 404, detail=str(exc)) from exc

    run_id = f"legacy-{uuid.uuid4()}"

    async def stream():
        accumulated_answer = ""
        worker_results: list[dict] = []
        compact_context: dict = {}
        try:
            yield _event({"type": "thread", "threadId": str(thread.id)})
            yield _event({"type": "status", "phase": "searching"})

            async for event in service.run_agent_graph_stream(
                repo_id,
                run_request.question,
                clone_path,
                run_id,
            ):
                if event.get("type") == "internal_state":
                    compact_context = event["compact_context"]
                    worker_results = event["worker_results"]
                    continue
                legacy_payload = _legacy_graph_event_payload(event)
                if legacy_payload:
                    yield _event(legacy_payload)

            yield _event({"type": "status", "phase": "generating"})
            async for event in service.stream_answer(
                repo_name=job.repo_name,
                user_query=run_request.question,
                compact_context=compact_context,
                worker_results=worker_results,
                mode=mode,
            ):
                if event.get("type") == "answer_delta":
                    accumulated_answer += event.get("content", "")
                legacy_payload = _legacy_graph_event_payload(event)
                if legacy_payload:
                    yield _event(legacy_payload)

            await service.persist_answer(thread, accumulated_answer, mode, worker_results)
            references = _references_from_worker_results(worker_results)
            if references:
                yield _event({"type": "references", "references": references})
            yield _event({"type": "done"})
        except Exception as exc:
            logger.exception("[ChatRouter] legacy SSE stream 오류 run=%s", run_id)
            await db.rollback()
            yield _event({"type": "error", "error": str(exc)})

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/{repo_id}/runs/{run_id}/stream")
async def stream_chat_run(repo_id: UUID, run_id: str, db: AsyncSession = Depends(get_db)):
    """
    LangGraph 멀티에이전트 SSE 스트리밍.
    """
    run_data = _RUN_STORE.pop(run_id, None)
    if not run_data:
        raise HTTPException(status_code=404, detail="Run not found or already consumed")

    request: ChatRunRequest = run_data["request"]
    clone_path = run_data["clone_path"]
    job = run_data["job"]
    thread = run_data["thread"]
    mode = run_data["mode"]
    service = RepositoryChatService(db)

    async def stream():
        accumulated_answer = ""
        worker_results = []
        try:
            yield _event({"type": "graph_started", "runId": run_id, "stateKeys": ["user_query"]})

            compact_context = {}
            # Graph Stream
            async for event in service.run_agent_graph_stream(repo_id, request.question, clone_path, run_id):
                if event.get("type") == "internal_state":
                    compact_context = event["compact_context"]
                    worker_results = event["worker_results"]
                    continue
                yield _event(event)

            # Final Answer Agent Stream
            async for event in service.stream_answer(
                repo_name=job.repo_name,
                user_query=request.question,
                compact_context=compact_context,
                worker_results=worker_results,
                mode=mode,
            ):
                if event.get("type") == "answer_delta":
                    accumulated_answer += event.get("content", "")
                yield _event(event)

            # DB 저장
            await service.persist_answer(thread, accumulated_answer, mode, worker_results)

            yield _event({"type": "completed", "runId": run_id, "status": "completed"})

        except Exception as exc:
            logger.exception("[ChatRouter] SSE stream 오류 run=%s", run_id)
            yield _event({"type": "failed", "runId": run_id, "error": str(exc)})
            if not accumulated_answer:
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
