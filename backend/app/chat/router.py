import asyncio
import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.repository import ChatRepository
from app.chat.schemas import ChatRequest
from app.chat.service import RepositoryChatService
from app.core.database import get_db


router = APIRouter(prefix="/api/chat", tags=["Repository Chat"])


def _event(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


@router.post("/{repo_id}")
async def chat(repo_id: UUID, request: ChatRequest, db: AsyncSession = Depends(get_db)):
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
