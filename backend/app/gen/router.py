"""
DOCS-GEN API 라우터 (DOCS-GEN-API-002, DOCS-GEN-API-005)

POST /api/gen/docs/{repo_id}      — 가이드북 생성 트리거 (API-002)
POST /api/gen/docs/{repo_id}/save — Markdown DB 저장 (API-005, 내부용)
"""

import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.database import get_db
from app.gen.schemas import (
    DocSaveRequest,
    DocSaveData,
    DocSaveResponse,
    DocTriggerRequest,
    DocTriggerData,
    DocTriggerResponse,
)
from app.gen.service import save_onboarding_doc, validate_and_queue_doc_generation

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gen/docs", tags=["DOCS GEN"])


# ──────────────────────────────────────────────────────────────
# DOCS-GEN-API-002: 가이드북 생성 트리거
# ──────────────────────────────────────────────────────────────
@router.post(
    "/{repo_id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=DocTriggerResponse,
    summary="온보딩 가이드북 생성 트리거 (DOCS-GEN-API-002)",
)
async def trigger_doc_generation(
    repo_id: UUID,
    body: DocTriggerRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> DocTriggerResponse:
    '''
    Map-Reduce 파이프라인으로 온보딩 가이드북 생성을 시작한다.

    즉시 202를 반환하고, 실제 생성 작업은 BackgroundTasks로 비동기 실행한다.

    에러 응답:
    - 404 REPO_NOT_FOUND:            저장소 없음
    - 409 DOCS_ALREADY_EXISTS:       force=false & 기존 가이드북 존재
    - 409 DOCS_GENERATION_IN_PROGRESS: 생성 진행 중
    - 422 ANALYSIS_NOT_COMPLETED:    RAG 파이프라인 미완료
    '''
    job_id, version = await validate_and_queue_doc_generation(
        db=db,
        repo_id=repo_id,
        force=body.force,
        background_tasks=background_tasks,
        model=body.model,
    )

    logger.info(
        "[DOCS-GEN-API-002] 생성 시작 | repo_id=%s job_id=%s version=%d",
        repo_id, job_id, version,
    )

    return DocTriggerResponse(
        data=DocTriggerData(
            job_id=job_id,
            repo_id=repo_id,
            status="docs_queued",
            estimated_minutes=2,
        )
    )


# ──────────────────────────────────────────────────────────────
# DOCS-GEN-API-005: Markdown DB 저장
# ──────────────────────────────────────────────────────────────
@router.post(
    "/{repo_id}/save",
    status_code=status.HTTP_201_CREATED,
    response_model=DocSaveResponse,
    summary="온보딩 가이드북 Markdown DB 저장 (DOCS-GEN-API-005)",
)
async def save_doc(
    repo_id: UUID,
    body: DocSaveRequest,
    db: AsyncSession = Depends(get_db),
) -> DocSaveResponse:
    '''
    생성된 Markdown 가이드북을 PostgreSQL docs 테이블에 저장한다.

    내부 파이프라인(DOCS-GEN-B-301)이 호출하는 API로,
    프론트엔드에서 직접 호출하지 않는다.

    - 404: repo_id에 해당하는 저장소가 없을 때 (REPO_NOT_FOUND)
    - 500: DB 저장 중 오류 (DATABASE_SAVE_FAILED)
    '''
    doc = await save_onboarding_doc(
        db=db,
        repo_id=repo_id,
        job_id=body.job_id,
        content=body.content,
        version=body.version,
    )

    logger.info(
        "[DOCS-GEN-API-005] 응답 | doc_id=%s repo_id=%s version=%d",
        doc.id, repo_id, body.version,
    )

    return DocSaveResponse(
        data=DocSaveData(
            doc_id=doc.id,
            repo_id=repo_id,
            version=doc.version,
        )
    )
