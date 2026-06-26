"""
WebSocket 엔드포인트 모듈 (API-006)

분석 작업의 진행 상태를 Frontend ProgressPanel에 WebSocket으로 실시간 push한다.
클라이언트가 연결하면 서버는 해당 job의 이벤트 큐를 구독하고,
각 파이프라인 단계 전환 시마다 JSON 이벤트를 push한다.

WS /ws/progress/{job_id}
"""

import json
import logging
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

from app.infra.database import async_session_factory
from app.pipeline.event_manager import event_manager
from app.repo.repository import AnalysisJobRepository
from app.pipeline.schemas import JobStatus

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# WebSocket 전용 라우터
# ──────────────────────────────────────────────
ws_router = APIRouter(tags=["WebSocket Progress"])

# WebSocket 커스텀 Close 코드 정의 (API-006 명세서 기반)
WS_CLOSE_POLICY_VIOLATION = 1008   # Authorization 인증 실패
WS_CLOSE_SERVER_ERROR = 1011       # 서버 내부 오류
WS_CLOSE_JOB_NOT_FOUND = 4004     # 존재하지 않는 job_id
WS_CLOSE_JOB_ALREADY_DONE = 4008  # 이미 완료/실패한 job_id


# ──────────────────────────────────────────────
# WebSocket 연결 핸들러: 분석 진행 상태 실시간 수신
# WS /ws/progress/{job_id}
# ──────────────────────────────────────────────
@ws_router.websocket("/ws/progress/{job_id}")
async def websocket_progress(websocket: WebSocket, job_id: str):
    """
    WebSocket 기반 분석 진행 상태 수신 엔드포인트

    1. 클라이언트 연결을 수락한다.
    2. job_id 유효성을 검증한다.
    3. 이벤트 큐를 구독하여 실시간 이벤트를 push한다.
    4. COMPLETED 또는 FAILED 이벤트 수신 후 연결을 자동 종료한다.

    WS Close Code:
      - 1008 (POLICY_VIOLATION): 인증 실패
      - 1011 (SERVER_ERROR): 서버 내부 오류
      - 4004 (JOB_NOT_FOUND): 존재하지 않는 job_id
      - 4008 (JOB_ALREADY_DONE): 이미 완료/실패 상태인 job
    """
    await websocket.accept()

    try:
        # 1. job_id가 유효한 UUID인지 유효성 검증 -> 아니면 close(4004)
        try:
            job_uuid = UUID(job_id)
        except ValueError:
            await websocket.close(
                code=WS_CLOSE_JOB_NOT_FOUND,
                reason="유효하지 않은 job_id 형식입니다."
            )
            return

        # 2. DB에서 job 존재 여부 및 상태 확인 -> 아니면 close(4004)
        async with async_session_factory() as session:
            repo = AnalysisJobRepository(session)
            job = await repo.get_job_by_id(job_uuid)

            if not job:
                await websocket.close(
                    code=WS_CLOSE_JOB_NOT_FOUND,
                    reason="존재하지 않는 분석 작업입니다."
                )
                return

            # 이미 완료/실패한 작업이면 연결 거부 -> close(4004)
            if job.status in (JobStatus.COMPLETED.value, JobStatus.FAILED.value):
                await websocket.close(
                    code=WS_CLOSE_JOB_ALREADY_DONE,
                    reason="이미 완료되었거나 실패한 분석 작업입니다."
                )
                return

        # 4. 이벤트 큐 구독 및 실시간 push
        logger.info(f"WebSocket 연결 수립 (job_id={job_id})")

        async for event in event_manager.subscribe(job_id):
            # WebSocket 연결 상태 확인
            if websocket.client_state != WebSocketState.CONNECTED:
                logger.info(f"WebSocket 클라이언트 연결 해제됨 (job_id={job_id})")
                break

            # JSON 이벤트를 클라이언트에게 push
            event_json = event.model_dump_json()
            await websocket.send_text(event_json)

            # 최종 상태 수신 시 정상 종료
            if event.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                logger.info(
                    f"분석 {event.status.value} — WebSocket 연결 종료 (job_id={job_id})"
                )
                await websocket.close(code=1000, reason=f"분석 {event.status.value}")
                return

    except WebSocketDisconnect as e:
        # 클라이언트가 연결을 끊은 경우 (정상)
        logger.info(
            f"WebSocket 클라이언트 연결 해제 (job_id={job_id}, code={e.code})"
        )

    except Exception as e:
        # 예상치 못한 오류 발생 시 서버 에러로 종료
        logger.error(f"WebSocket 오류 (job_id={job_id}): {e}")
        try:
            if websocket.client_state == WebSocketState.CONNECTED:
                await websocket.close(
                    code=WS_CLOSE_SERVER_ERROR,
                    reason="서버 내부 오류가 발생했습니다."
                )
        except Exception:
            pass
