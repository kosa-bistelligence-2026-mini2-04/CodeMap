"""
Run 레지스트리 — Agent run의 생명주기 상태와 실행 결과를 보존합니다.

run 생성, SSE stream, status/evidence/cancel 조회가 같은 RunRecord를
공유하도록 하여 stream 완료 후에도 실행 결과를 조회할 수 있게 합니다.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from uuid import UUID

if TYPE_CHECKING:
    from app.repo.models import AnalysisJob


@dataclass
class RunRecord:
    """하나의 Agent run 실행 기록."""

    run_id: str
    repo_id: UUID
    session_id: str

    # 실행 준비 데이터 (create_chat_run에서 저장)
    request: Any = None  # ChatRunRequest
    thread: dict[str, Any] = field(default_factory=dict)
    job: AnalysisJob | None = None
    clone_path: str = ""
    mode: str = "standard"

    # 상태 추적
    status: str = "queued"  # queued → running → streaming → completed | failed | cancelled
    current_node: str | None = None
    created_at: float = field(default_factory=time.time)
    started_at: float | None = None
    completed_at: float | None = None

    # 실행 결과 (stream 중 누적, 완료 후 보존)
    worker_results: list[dict[str, Any]] = field(default_factory=list)
    compact_context: dict[str, Any] = field(default_factory=dict)
    accumulated_answer: str = ""
    references: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    durations: dict[str, float] = field(default_factory=dict)
    error: str | None = None

    # 취소 제어
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)
    transition_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    @property
    def is_terminal(self) -> bool:
        return self.status in ("completed", "failed", "cancelled")

    @property
    def elapsed_seconds(self) -> float | None:
        if self.started_at is None:
            return None
        end = self.completed_at or time.time()
        return round(end - self.started_at, 3)

    @property
    def completed_at_iso(self) -> str | None:
        if self.completed_at is None:
            return None
        return datetime.fromtimestamp(self.completed_at, tz=timezone.utc).isoformat()

    async def claim_for_stream(self) -> bool:
        """Atomically claim a queued run for the single active execution stream."""
        async with self.transition_lock:
            if self.status != "queued":
                return False
            self.status = "running"
            self.current_node = "graph_started"
            self.started_at = time.time()
            return True

    async def mark_cancelled(self) -> bool:
        """Move to cancelled unless another terminal state already won."""
        async with self.transition_lock:
            if self.is_terminal:
                return False
            self.cancel_event.set()
            self.status = "cancelled"
            self.current_node = None
            self.completed_at = time.time()
            return True

    async def mark_completed(self) -> bool:
        """Move to completed only if cancellation/failure did not already win."""
        async with self.transition_lock:
            if self.is_terminal or self.cancel_event.is_set():
                return False
            self.status = "completed"
            self.current_node = None
            self.completed_at = time.time()
            return True

    async def mark_failed(self, error: str) -> bool:
        """Move to failed unless a terminal state already won."""
        async with self.transition_lock:
            if self.is_terminal:
                return False
            self.status = "failed"
            self.error = error
            self.current_node = None
            self.completed_at = time.time()
            return True

    def to_status_response(self) -> dict[str, Any]:
        """GET /runs/{run_id} 응답용 dict."""
        state_keys = ["user_query"]
        if self.compact_context:
            state_keys.extend(["rewritten_query", "access_plan", "security_result",
                               "worker_results", "compact_context"])
        elif self.worker_results:
            state_keys.extend(["rewritten_query", "access_plan", "security_result",
                               "worker_results"])

        planner_event = next((e for e in self.events if e.get("type") == "planner_plan"), {})
        route_event = next((e for e in self.events if e.get("type") == "route_validated"), {})

        return {
            "code": 200,
            "message": "success",
            "data": {
                "runId": self.run_id,
                "sessionId": self.session_id,
                "status": self.status,
                "currentNode": self.current_node,
                "state": {
                    "userQuery": self.request.question if self.request else "",
                    "rewrittenQuery": planner_event.get("rewrittenQuery", ""),
                    "accessPlan": {
                        "selectedWorkers": planner_event.get("selectedWorkers", []),
                        "allowedPaths": planner_event.get("allowedPaths", []),
                    },
                    "securityResult": {
                        "allowed": route_event.get("allowed"),
                        "parallelGroups": route_event.get("parallelGroups", []),
                    },
                    "workerResultCount": len(self.worker_results),
                    "compactContextReady": bool(self.compact_context),
                    "stateKeys": state_keys,
                },
                "durations": self.durations,
                "finalAnswer": {
                    "length": len(self.accumulated_answer),
                    "referenceCount": len(self.references),
                    "elapsedSeconds": self.elapsed_seconds,
                } if self.accumulated_answer else None,
                "error": self.error,
            },
        }

    def to_evidence_response(
        self,
        include_raw_snippet: bool = False,
        worker_filter: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """GET /runs/{run_id}/evidence 응답용 dict."""
        evidence = self.worker_results
        if worker_filter:
            evidence = [e for e in evidence
                        if e.get("metadata", {}).get("worker") == worker_filter]
        evidence = evidence[:limit]

        items = []
        for e in evidence:
            item = {
                "id": e.get("id", ""),
                "worker": e.get("metadata", {}).get("worker", ""),
                "path": e.get("path", ""),
                "lineStart": e.get("lineStart"),
                "lineEnd": e.get("lineEnd"),
                "score": e.get("score"),
            }
            if include_raw_snippet:
                item["snippet"] = e.get("snippet", "")
            items.append(item)

        return {
            "code": 200,
            "message": "success",
            "data": {
                "runId": self.run_id,
                "evidence": items,
                "compactContext": self.compact_context if self.compact_context else None,
                "stateField": "worker_results",
            },
        }


class RunRegistry:
    """메모리 기반 Run 레지스트리. 단일 프로세스 환경용."""

    def __init__(self) -> None:
        self._runs: dict[str, RunRecord] = {}

    def create(self, run_id: str, repo_id: UUID, session_id: str, **kwargs) -> RunRecord:
        record = RunRecord(run_id=run_id, repo_id=repo_id, session_id=session_id, **kwargs)
        self._runs[run_id] = record
        return record

    def get(self, run_id: str) -> RunRecord | None:
        return self._runs.get(run_id)

    def list_by_repo(self, repo_id: UUID) -> list[RunRecord]:
        return [r for r in self._runs.values() if r.repo_id == repo_id]

    def cleanup_old(self, max_age_seconds: int = 3600) -> int:
        """1시간 이상 된 완료 run을 정리합니다."""
        now = time.time()
        to_remove = [
            rid for rid, r in self._runs.items()
            if r.is_terminal and (now - r.created_at) > max_age_seconds
        ]
        for rid in to_remove:
            del self._runs[rid]
        return len(to_remove)


async def sweep_run_registry(interval_seconds: int = 300, max_age_seconds: int = 3600) -> None:
    """Periodically prune terminal in-memory run records in single-process deployments."""
    while True:
        await asyncio.sleep(interval_seconds)
        run_registry.cleanup_old(max_age_seconds=max_age_seconds)


# 싱글톤 인스턴스
run_registry = RunRegistry()
