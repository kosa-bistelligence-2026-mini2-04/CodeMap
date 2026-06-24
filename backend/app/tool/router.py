"""
외부 MCP 신호 수신 및 도구 Job 실행을 위한 API 라우터 (Phase 2).
"""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["tools"])


# ──────────────────────────────────────────────
# MCP 도구 Job 실행 엔드포인트
# ──────────────────────────────────────────────
@router.post("/execute")
async def execute_tool_job(
    job_id: UUID,
    run_id: UUID,
    tool_name: str,
    arguments: dict,
    db: AsyncSession = Depends(get_db),
):
    '''
    외부 혹은 에이전트로부터 요청받은 MCP 표준 I/O 도구 실행 요청을 처리합니다.
    (Phase 2 수신 라우터 표준 뼈대 구현)
    '''
    logger.info(
        "[ToolRouter] 실행 요청 수신 — tool=%s, job_id=%s",
        tool_name,
        job_id,
    )

    from app.tool.service import CodeMapToolService

    service = CodeMapToolService()
    result = await service.execute_job(
        job_id=job_id,
        run_id=run_id,
        tool_name=tool_name,
        arguments=arguments,
    )
    return {"status": "success", "result": result}
