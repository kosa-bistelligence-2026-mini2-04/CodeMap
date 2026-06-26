"""
DOCS-GEN API 라우터 (DOCS-GEN-API-005)

POST /api/gen/docs/{repo_id}/save — Markdown DB 저장 (내부 파이프라인 호출용)
"""

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.database import get_db
from app.gen.schemas import DocSaveRequest, DocSaveData, DocSaveResponse
from app.gen.service import save_onboarding_doc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gen/docs", tags=["DOCS GEN"])


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
