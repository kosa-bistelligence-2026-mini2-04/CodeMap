"""
PROJECT-LIST-API-003 실시간 진행률 공유 WebSocket 엔드포인트입니다.

기존 파이프라인 이벤트 브로커를 구독하되, LIST 명세에서 요구하는 메시지 필드명으로 변환해 전송합니다.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.core.database import async_session_factory
from app.list.schemas import AnalysisProgressMessage
from app.repo.event_manager import event_manager
from app.repo.repository import AnalysisJobRepository
from app.repo.schemas import JobStatus, ProgressEvent

logger = logging.getLogger(__name__)

ws_router = APIRouter(tags=["Project List Progress"])

WS_CLOSE_SERVER_ERROR = 1011
WS_CLOSE_JOB_NOT_FOUND = 4004


def _to_api_status(status: str | JobStatus) -> str:
    """내부 작업 상태를 LIST 명세의 상태값으로 변환합니다."""
    value = status.value if isinstance(status, JobStatus) else status
    status_map = {
        JobStatus.IN_PROGRESS.value: "running",
        JobStatus.CLONED.value: "queued",
        JobStatus.COMPLETED.value: "completed",
        JobStatus.FAILED.value: "failed",
    }
    return status_map.get(value, value.lower())


def _is_failed(status: str | JobStatus) -> bool:
    """실패 상태인지 확인합니다."""
    value = status.value if isinstance(status, JobStatus) else status
    return value in {JobStatus.FAILED.value, "failed"}


def _message_from_event(job_id: UUID, event: ProgressEvent) -> AnalysisProgressMessage:
    """파이프라인 이벤트를 API-003 WebSocket 메시지로 변환합니다."""
    failed = _is_failed(event.status)
    return AnalysisProgressMessage(
        jobId=job_id,
        status=_to_api_status(event.status),
        progress=event.progress,
        currentStep=event.stage.value,
        failedAgent=event.stage.value if failed else None,
        errorMessage=event.message if failed else None,
    )


def _message_from_job(job) -> AnalysisProgressMessage:
    """DB의 현재 작업 상태를 API-003 WebSocket 메시지로 변환합니다."""
    failed = _is_failed(job.status)
    return AnalysisProgressMessage(
        jobId=job.id,
        status=_to_api_status(job.status),
        progress=job.progress,
        currentStep=job.stage,
        failedAgent=job.stage if failed else None,
        errorMessage=job.message if failed else None,
    )


@ws_router.websocket("/ws/list/progress/{job_id}")
async def websocket_list_progress(websocket: WebSocket, job_id: str):
    """분석 작업의 진행 상태를 LIST 명세 포맷으로 실시간 전송합니다."""
    await websocket.accept()

    try:
        try:
            job_uuid = UUID(job_id)
        except ValueError:
            await websocket.close(
                code=WS_CLOSE_JOB_NOT_FOUND,
                reason="유효하지 않은 job_id 형식입니다.",
            )
            return

        async with async_session_factory() as session:
            repository = AnalysisJobRepository(session)
            job = await repository.get_job_by_id(job_uuid)
            if not job:
                await websocket.close(
                    code=WS_CLOSE_JOB_NOT_FOUND,
                    reason="존재하지 않는 분석 작업입니다.",
                )
                return

            # 늦게 접속한 화면도 현재 상태를 즉시 표시할 수 있도록 DB 상태를 먼저 전송합니다.
            current_message = _message_from_job(job)
            await websocket.send_text(current_message.model_dump_json())
            if current_message.status in {"completed", "failed"}:
                await websocket.close(code=1000, reason=f"분석 {current_message.status}")
                return

        logger.info("LIST 진행률 WebSocket 연결 수립 (job_id=%s)", job_id)

        async for event in event_manager.subscribe(job_id):
            if websocket.client_state != WebSocketState.CONNECTED:
                logger.info("LIST 진행률 WebSocket 연결 해제 감지 (job_id=%s)", job_id)
                break

            message = _message_from_event(job_uuid, event)
            await websocket.send_text(message.model_dump_json())

            if message.status in {"completed", "failed"}:
                await websocket.close(code=1000, reason=f"분석 {message.status}")
                return

    except WebSocketDisconnect as exc:
        logger.info("LIST 진행률 WebSocket 클라이언트 연결 해제 (job_id=%s, code=%s)", job_id, exc.code)

    except Exception as exc:
        logger.exception("LIST 진행률 WebSocket 오류 (job_id=%s)", job_id)
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close(
                    code=WS_CLOSE_SERVER_ERROR,
                    reason="서버 내부 오류가 발생했습니다.",
                )
        except Exception:
            logger.debug("LIST 진행률 WebSocket 오류 종료 중 추가 예외 발생", exc_info=True)
