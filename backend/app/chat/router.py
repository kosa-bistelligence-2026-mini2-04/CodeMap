import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.repository import ChatRepository
from app.chat.schemas import ChatRequest
from app.chat.service import RepositoryChatService
from app.core.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Repository Chat"])


def _event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/{repo_id}")
async def chat(repo_id: UUID, request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    LangGraph 멀티에이전트 기반 저장소 대화 엔드포인트.

    SSE 이벤트 순서:
      thread      — 스레드 ID
      status      — searching / building_context / generating
      exploration — Worker가 탐색한 파일 이력 (실시간)
      content     — LLM 응답 토큰 스트림
      references  — 최종 참조 파일 목록
      done        — 완료 신호
      error       — 오류 발생 시
    """
    service = RepositoryChatService(db)

    try:
        job, thread, mode, clone_path = await service.prepare(repo_id, request)
    except ValueError as exc:
        if "스냅샷이 아직 준비" in str(exc):
            # 스냅샷 미준비 — 안내 메시지 SSE 스트림 반환
            async def _fallback_stream():
                yield _event({"type": "status", "phase": "generating"})
                msg = (
                    "⚠️ 아직 저장소 스냅샷 분석이 완료되지 않아 전체 구조 기반 탐색을 수행할 수 없습니다.\n\n"
                    "하지만 **단일 코드 스니펫 해석**, **일반적인 프로그래밍 질문**, "
                    "**오류 메시지 원인 파악** 등은 현재도 도움을 드릴 수 있습니다."
                )
                chunk_size = 36
                for i in range(0, len(msg), chunk_size):
                    yield _event({"type": "content", "content": msg[i:i + chunk_size]})
                yield _event({"type": "suggestions", "suggestions": [
                    "에러 메시지 의미 해석",
                    "단편적인 코드 리뷰",
                    "특정 프레임워크 사용법",
                ]})
                yield _event({"type": "done"})

            return StreamingResponse(
                _fallback_stream(),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache"},
            )
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    # ── LangGraph 멀티에이전트 스트리밍 SSE ──
    async def stream():
        accumulated_answer = ""
        worker_results: list[dict] = []
        try:
            yield _event({"type": "thread", "threadId": str(thread.id)})
            yield _event({"type": "status", "phase": "searching"})

            # 1. LangGraph 실행 (Supervisor → Route → Workers → Aggregator)
            user_query = request.message
            if request.contextFile:
                user_query = f"{request.contextFile} 파일 컨텍스트: {user_query}"

            graph_result = await service.run_agent_graph(
                repo_id=repo_id,
                user_query=user_query,
                clone_path=clone_path,
                mode=mode,
            )
            worker_results = graph_result.get("worker_results", [])
            compact_context = graph_result.get("compact_context", {})

            yield _event({"type": "status", "phase": "building_context"})

            # 2. Final Answer Agent 스트리밍
            async for event in service.stream_answer(
                repo_name=job.repo_name,
                user_query=request.message,
                compact_context=compact_context,
                worker_results=worker_results,
                mode=mode,
            ):
                if event.get("type") == "content":
                    accumulated_answer += event.get("content", "")
                yield _event(event)

            # 3. DB 저장
            await service.persist_answer(thread, accumulated_answer, mode, worker_results)

        except Exception as exc:
            logger.exception("[ChatRouter] SSE stream 오류 repo=%s", repo_id)
            yield _event({"type": "error", "message": "답변 생성 중 오류가 발생했습니다. 다시 시도해주세요."})
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
