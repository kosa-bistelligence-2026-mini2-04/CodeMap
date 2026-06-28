"""
에이전트 Run 관리 API 라우터.

Run 상태 조회, 실행 취소, 근거(evidence) 조회를 담당합니다.
(LLM_RUN_MANAGEMENT_API_SPEC — LLM-CHAT-API-003 ~ 005)
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.run_registry import run_registry
from app.infra.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Agent Run Management"])


def _status_repo_id(status: dict) -> UUID | None:
    try:
        value = status.get("data", {}).get("repoId")
        return UUID(str(value)) if value else None
    except (TypeError, ValueError):
        logger.warning("[AgentRouter] Redis Run 상태 repoId 파싱 실패")
        return None


# ──────────────────────────────────────────────
# LLM-CHAT-API-003: Run 상태 및 State 요약 조회
# ──────────────────────────────────────────────
@router.get("/{repo_id}/runs/{run_id}")
async def get_run_status(
    repo_id: UUID,
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Run 실행 상태, node별 소요 시간, State 요약 조회."""
    logger.info("[AgentRouter] Run 상태 조회 — run_id=%s", run_id)
    status = await run_registry.get_status(run_id)
    if not status or _status_repo_id(status) != repo_id:
        raise HTTPException(status_code=404, detail="Run not found")
    status["data"].pop("repoId", None)
    return status


# ──────────────────────────────────────────────
# LLM-CHAT-API-004: Run 취소
# ──────────────────────────────────────────────
@router.post("/{repo_id}/runs/{run_id}/cancel")
async def cancel_run(
    repo_id: UUID,
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """실행 중인 LangGraph/worker run 취소."""
    logger.info("[AgentRouter] Run 취소 요청 — run_id=%s", run_id)
    status = await run_registry.get_status(run_id)
    if not status or _status_repo_id(status) != repo_id:
        raise HTTPException(status_code=404, detail="Run not found")
    if status["data"]["status"] in ("completed", "failed", "cancelled"):
        raise HTTPException(status_code=409, detail="Run already finished")

    await run_registry.request_cancel(run_id)
    from datetime import datetime, timezone
    return {
        "code": 200,
        "message": "cancelled",
        "data": {
            "runId": run_id,
            "status": "cancelled",
            "cancelledAt": datetime.now(timezone.utc).isoformat(),
        },
    }


# ──────────────────────────────────────────────
# LLM-CHAT-API-005: 근거(Evidence) 조회
# ──────────────────────────────────────────────
@router.get("/{repo_id}/runs/{run_id}/evidence")
async def get_run_evidence(
    repo_id: UUID,
    run_id: str,
    include_raw_snippet: bool = Query(False, alias="includeRawSnippet"),
    worker: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Worker evidence 및 compact context 조회."""
    logger.info("[AgentRouter] Evidence 조회 — run_id=%s, worker=%s", run_id, worker)
    evidence = await run_registry.get_evidence(run_id, include_raw_snippet, worker, limit)
    if not evidence:
        status = await run_registry.get_status(run_id)
        if not status or _status_repo_id(status) != repo_id:
            raise HTTPException(status_code=404, detail="Run not found")
        raise HTTPException(status_code=404, detail="Evidence not found")
    if _status_repo_id(evidence) != repo_id:
        raise HTTPException(status_code=404, detail="Run not found")
    evidence.get("data", {}).pop("repoId", None)
    
    if not evidence.get("data", {}).get("evidence") and not evidence.get("data", {}).get("compactContext"):
        raise HTTPException(status_code=404, detail="Evidence not found")
        
    return evidence
