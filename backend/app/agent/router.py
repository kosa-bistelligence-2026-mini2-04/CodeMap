"""
에이전트 Run 관리 API 라우터.

Run 상태 조회, 실행 취소, 근거(evidence) 조회를 담당합니다.
(LLM_RUN_MANAGEMENT_API_SPEC — LLM-CHAT-API-003 ~ 005)
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["Agent Run Management"])


# ──────────────────────────────────────────────
# LLM-CHAT-API-003: Run 상태 및 State 요약 조회
# ──────────────────────────────────────────────
@router.get("/{repo_id}/runs/{run_id}", status_code=501)
async def get_run_status(
    repo_id: UUID,
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Run 실행 상태, node별 소요 시간, State 요약 조회 (구현 예정)."""
    logger.info("[AgentRouter] Run 상태 조회 — run_id=%s", run_id)
    return {
        "code": 501,
        "message": "not_implemented",
        "detail": "Run status query is not yet implemented. See LLM-CHAT-API-003.",
    }


# ──────────────────────────────────────────────
# LLM-CHAT-API-004: Run 취소
# ──────────────────────────────────────────────
@router.post("/{repo_id}/runs/{run_id}/cancel", status_code=501)
async def cancel_run(
    repo_id: UUID,
    run_id: str,
    db: AsyncSession = Depends(get_db),
):
    """실행 중인 LangGraph/worker run 취소 (구현 예정)."""
    logger.info("[AgentRouter] Run 취소 요청 — run_id=%s", run_id)
    return {
        "code": 501,
        "message": "not_implemented",
        "detail": "Run cancellation is not yet implemented. See LLM-CHAT-API-004.",
    }


# ──────────────────────────────────────────────
# LLM-CHAT-API-005: 근거(Evidence) 조회
# ──────────────────────────────────────────────
@router.get("/{repo_id}/runs/{run_id}/evidence", status_code=501)
async def get_run_evidence(
    repo_id: UUID,
    run_id: str,
    include_raw_snippet: bool = Query(False, alias="includeRawSnippet"),
    worker: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Worker evidence 및 compact context 조회 (구현 예정)."""
    logger.info("[AgentRouter] Evidence 조회 — run_id=%s, worker=%s", run_id, worker)
    return {
        "code": 501,
        "message": "not_implemented",
        "detail": "Evidence query is not yet implemented. See LLM-CHAT-API-005.",
    }
