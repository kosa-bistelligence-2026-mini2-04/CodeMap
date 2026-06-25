"""
외부 MCP 신호 수신 및 도구 Job 실행을 위한 API 라우터 (Phase 2).
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.database import get_db
from app.tool.service import CodeMapToolService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tools", tags=["tools"])


class ToolExecuteRequest(BaseModel):
    tool_name: str
    arguments: dict
    job_id: str | None = None
    run_id: str | None = None


# ──────────────────────────────────────────────
# MCP 도구 Job 실행 엔드포인트
# ──────────────────────────────────────────────
@router.post("/execute")
async def execute_tool_job(
    request: ToolExecuteRequest,
    db: AsyncSession = Depends(get_db),
):
    '''
    외부 혹은 에이전트로부터 요청받은 MCP 표준 I/O 도구 실행 요청을 처리합니다.
    '''
    job_id = _parse_uuid(request.job_id, "job_id")
    run_id = _parse_uuid(request.run_id, "run_id")
    logger.info(
        "[ToolRouter] 실행 요청 — tool=%s, job_id=%s",
        request.tool_name,
        request.job_id,
    )

    try:
        return await CodeMapToolService(db).execute_job(
            job_id=job_id,
            run_id=run_id,
            tool_name=request.tool_name,
            arguments=request.arguments,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _parse_uuid(value: str | None, field_name: str) -> uuid.UUID:
    if not value:
        return uuid.uuid4()
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{field_name} must be a valid UUID") from exc
