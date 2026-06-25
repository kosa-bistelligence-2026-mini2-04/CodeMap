"""
이벤트 큐 관리 모듈 (Event Broker)

SSE(API-005)와 WebSocket(API-006)이 동일한 진행 상태 이벤트를
공유할 수 있도록 asyncio 기반 Pub/Sub 이벤트 브로커를 제공한다.
각 job_id별로 독립적인 이벤트 큐를 관리한다.
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import AsyncGenerator
from uuid import UUID

from app.repo.schemas import ProgressEvent, JobStatus, PipelineStage

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# 이벤트 매니저 싱글톤 클래스
# ──────────────────────────────────────────────
class EventManager:
    """
    분석 파이프라인 이벤트 브로커

    job_id별로 구독자(subscriber) 목록을 관리하며,
    파이프라인 단계 전환 시 publish된 이벤트를 모든 구독자에게 배포한다.
    SSE 엔드포인트와 WebSocket 엔드포인트 모두 이 매니저를 통해 이벤트를 수신한다.
    """

    def __init__(self):
        # job_id별로 → 구독자 asyncio.Queue 리스트를 관리
        self._subscribers: dict[str, list[asyncio.Queue]] = defaultdict(list)
        # job_id → 마지막 이벤트 (늦게 접속한 구독자에게 현재 상태 제공용)
        self._last_events: dict[str, ProgressEvent] = {}
        # 백그라운드 정리 태스크가 GC로 사라지지 않도록 완료 전까지 참조 유지
        self._task_refs: set[asyncio.Task] = set()
        # 동시성 보장을 위한 락
        self._lock = asyncio.Lock()

    async def publish(self, job_id: str, event: ProgressEvent) -> None:
        """
        특정 job의 모든 구독자에게 이벤트를 배포한다.

        Args:
            job_id: 분석 작업 고유 ID
            event: 진행 상태 이벤트 데이터
        """
        # 연결이 끊긴 구독자 제거를 위한 유효 큐 목록
        async with self._lock:
            self._last_events[job_id] = event # 마지막 이벤트 저장
            active_queues = []
            for queue in self._subscribers[job_id]:
                try:
                    await queue.put(event) # 각 구독자의 큐에 이벤트 넣기
                    active_queues.append(queue)
                except Exception:
                    logger.warning(f"구독자 큐에 이벤트 전송 실패 (job_id={job_id})")

            self._subscribers[job_id] = active_queues

        # 최종 상태(COMPLETED/FAILED)인 경우 해당 job의 구독 정보를 정리한다
        if event.status in (JobStatus.COMPLETED, JobStatus.FAILED):
            self._create_tracked_task(self._cleanup_job(job_id))

    async def subscribe(self, job_id: str) -> AsyncGenerator[ProgressEvent, None]:
        """
        특정 job의 이벤트를 구독하는 비동기 제너레이터

        새로운 구독자가 접속하면 큐를 생성하고,
        이벤트가 publish될 때마다 yield한다.

        Args:
            job_id: 구독할 분석 작업 고유 ID

        Yields:
            ProgressEvent: 파이프라인 진행 상태 이벤트
        """
        queue: asyncio.Queue = asyncio.Queue()
        async with self._lock:
            self._subscribers[job_id].append(queue) # 구독 등록

        try:
            # 마지막 이벤트가 있으면 현재 상태를 즉시 전달 (늦게 접속하더라도 현재 상태를 알 수 있음)
            last_event = self._last_events.get(job_id)
            if last_event:
                yield last_event

            while True:
                event = await queue.get() # 이벤트가 올때까지 대기
                yield event

                # 최종 상태 수신 시 구독 종료
                if event.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                    break
        finally:
            # 구독 해제: 큐를 구독자 목록에서 제거
            async with self._lock:
                if queue in self._subscribers.get(job_id, []):
                    self._subscribers[job_id].remove(queue)

    def get_last_event(self, job_id: str) -> ProgressEvent | None:
        """특정 job의 마지막 이벤트를 조회한다 (현재 상태 확인용)"""
        return self._last_events.get(job_id)

    async def _cleanup_job(self, job_id: str) -> None:
        """완료/실패한 job의 구독 정보 및 캐시를 정리한다"""
        # 1. 큐 구독자 즉시 정리 (이벤트는 이미 전달 완료됨)
        await asyncio.sleep(1)
        async with self._lock:
            self._subscribers.pop(job_id, None)
        
        # 2. 10분 후 마지막 이벤트 캐시 제거 (메모리 누수 방지)
        # 클라이언트가 늦게 상태를 조회할 수 있도록 여유 시간을 둠
        self._create_tracked_task(self._delayed_cache_cleanup(job_id, delay=600))
        logger.info(f"이벤트 구독 정리 완료 및 캐시 삭제 예약 (job_id={job_id})")

    async def _delayed_cache_cleanup(self, job_id: str, delay: int) -> None:
        """지연 후 캐시를 삭제하는 백그라운드 태스크"""
        await asyncio.sleep(delay)
        async with self._lock:
            self._last_events.pop(job_id, None)
        logger.info(f"이벤트 캐시 정리 완료 (job_id={job_id})")

    def _create_tracked_task(self, coro) -> asyncio.Task:
        """백그라운드 태스크 참조를 완료 시점까지 보관한다."""
        task = asyncio.create_task(coro)
        self._task_refs.add(task)
        task.add_done_callback(self._task_refs.discard)
        return task


# ──────────────────────────────────────────────
# 이벤트 매니저 싱글톤 인스턴스
# ──────────────────────────────────────────────
event_manager = EventManager()
