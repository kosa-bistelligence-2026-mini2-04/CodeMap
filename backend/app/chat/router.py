import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.repository import ChatRepository
from app.chat.schemas import ChatContextRequest, ChatContextResponse, ChatRequest
from app.chat.service import RepositoryChatService
from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.schemas import ErrorResponse


router = APIRouter(prefix="/api/chat", tags=["Repository Chat"])


def _event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# ──────────────────────────────────────────────
# AGENT-CHAT-API-002: 코드 컨텍스트 검색
# POST /api/chat/{repo_id}/context
# ──────────────────────────────────────────────
@router.post(
    "/{repo_id}/context",
    response_model=ChatContextResponse,
    summary="코드 컨텍스트 검색",
    description="자연어 질문을 기반으로 분석 저장소의 코드 청크를 벡터 유사도 순으로 조회합니다.",
    responses={
        401: {"model": ErrorResponse, "description": "인증 토큰 누락 또는 만료"},
        404: {"model": ErrorResponse, "description": "분석 저장소를 찾을 수 없음"},
        500: {"model": ErrorResponse, "description": "벡터 검색 실패"},
    },
)
async def get_chat_context(
    repo_id: UUID,
    request: ChatContextRequest,
    db: AsyncSession = Depends(get_db),
    _current_user: dict = Depends(get_current_user),
) -> ChatContextResponse:
    """
    AGENT-CHAT-API-002 명세에 맞춰 질문과 관련된 코드 컨텍스트를 반환합니다.

    인증된 사용자의 요청을 받아 서비스 계층으로 검색 조건을 전달하고,
    표준 성공 응답 DTO 형태로 결과를 내려줍니다.
    """
    service = RepositoryChatService(db)
    return await service.get_context(repo_id, request)


# ──────────────────────────────────────────────
# AGENT-CHAT-API-001: Repo Chat SSE 스트리밍
# POST /api/chat/{repo_id}
# ──────────────────────────────────────────────
@router.post("/{repo_id}")
async def chat(repo_id: UUID, request: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    저장소에 대한 자연어 질문을 받아 SSE 스트리밍 답변을 반환합니다.

    현재 구현은 기존 채팅 화면의 이벤트 형식을 유지하며,
    명세 기준 이벤트 포맷 정리는 이후 순서에서 별도로 진행합니다.
    """
    service = RepositoryChatService(db)
    try:
        job, thread, mode, references = await service.prepare(repo_id, request)
    except ValueError as exc:
        if str(exc) == "저장소 스냅샷이 아직 준비되지 않았습니다.":
            async def fallback_stream():
                yield _event({"type": "status", "phase": "generating"})
                answer = (
                    "⚠️ 아직 저장소 스냅샷 분석이 완료되지 않아 전체 아키텍처나 구조 기반 탐색을 수행할 수 없습니다.\n\n"
                    "하지만 **단일 코드 스니펫 해석**, **일반적인 프로그래밍 지문**, **오류 메시지 원인 파악** 등은 "
                    "현재 상태에서도 바로 답변해 드릴 수 있습니다."
                )
                for index in range(0, len(answer), 36):
                    yield _event({"type": "content", "content": answer[index:index + 36]})
                    await asyncio.sleep(0.01)
                yield _event({"type": "suggestions", "suggestions": [
                    "에러 메시지 의미 해석",
                    "단편적인 코드 리뷰",
                    "특정 프레임워크 사용법"
                ]})
                yield _event({"type": "done"})
            return StreamingResponse(fallback_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def stream():
        answer = None
        try:
            yield _event({"type": "thread", "threadId": str(thread.id)})
            yield _event({"type": "status", "phase": "searching"})
            for item in references:
                yield _event({"type": "exploration", "step": f"{item['file']}:{item['line']} 확인"})
            yield _event({"type": "status", "phase": "building_context"})
            answer = await service.answer(job.repo_name, request, references, mode)
            yield _event({"type": "status", "phase": "generating"})
            for index in range(0, len(answer), 36):
                yield _event({"type": "content", "content": answer[index:index + 36]})
                await asyncio.sleep(0.01)
            yield _event({"type": "references", "references": references})
            await service.persist_answer(thread, answer, mode, references)
            yield _event({"type": "done"})
        except Exception as exc:
            # 스트리밍 중 오류 발생 시 에러 이벤트 전송 후 정리
            import logging
            logging.getLogger(__name__).exception("SSE stream failed for repo %s", repo_id)
            yield _event({"type": "error", "message": "답변 생성 중 오류가 발생했습니다. 다시 시도해주세요."})
            # 답변이 생성되지 않았으면 user 메시지도 롤백
            if answer is None:
                await db.rollback()

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


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
