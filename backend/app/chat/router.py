import json
import logging
import uuid
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.repository import ChatRepository
from app.chat.schemas import ChatRunRequest
from app.chat.service import RepositoryChatService
from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Repository Chat"])

# 임시 메모리 저장소 (DB 모델 대신 API 명세 맞춤용)
_RUN_STORE: dict[str, dict] = {}


def _event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


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
