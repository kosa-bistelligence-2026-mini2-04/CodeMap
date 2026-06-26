"""
DOCS-GEN 서비스 계층 (DOCS-GEN-B-301: Markdown 저장)

생성된 온보딩 가이드북 Markdown을 PostgreSQL에 저장하는
비즈니스 로직을 담당한다.

DOCS_GEN_SPEC.md B-301 구현 노트:
  - docs 테이블: repo_id, job_id, doc_type, content, version, created_at
  - 최신 버전 조회 최적화 (idx_docs_repo_id 인덱스 활용)
"""

import logging
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import DatabaseSaveFailedError, RepoNotFoundError
from app.gen.models import OnboardingDoc
from app.gen.repository import GenDocRepository

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────
# DOCS-GEN-B-301: Markdown DB 저장
# ──────────────────────────────────────────────────────────────
async def save_onboarding_doc(
    db: AsyncSession,
    repo_id: UUID,
    job_id: UUID,
    content: str,
    version: int,
) -> OnboardingDoc:
    '''
    온보딩 가이드북 Markdown을 PostgreSQL docs 테이블에 저장한다.

    DOCS-GEN-B-301 구현:
      1. repo_id 존재 여부 확인 (없으면 404 RepoNotFoundError)
      2. OnboardingDoc 레코드 저장
      3. commit 후 저장된 엔티티 반환

    Args:
        db:      AsyncSession (외부 주입)
        repo_id: 대상 저장소 ID (analysis_jobs.id)
        job_id:  문서 생성을 트리거한 분석 작업 ID
        content: 저장할 Markdown 가이드북 전문
        version: 가이드북 버전 번호

    Returns:
        저장된 OnboardingDoc 엔티티

    Raises:
        RepoNotFoundError (404):      repo_id에 해당하는 저장소가 없을 때
        DatabaseSaveFailedError (500): DB 저장 중 예외 발생 시
    '''
    repo = GenDocRepository(db)

    ## 1. 저장소 존재 여부 확인
    analysis_job = await repo.get_repo_by_id(repo_id)
    if analysis_job is None:
        logger.warning(
            "[DOCS-GEN-B-301] 저장소 없음 | repo_id=%s", repo_id
        )
        raise RepoNotFoundError()

    ## 2. 문서 저장
    try:
        doc = await repo.save_doc(
            repo_id=repo_id,
            job_id=job_id,
            content=content,
            version=version,
        )
        await db.commit()
        logger.info(
            "[DOCS-GEN-B-301] 저장 완료 | doc_id=%s repo_id=%s version=%d",
            doc.id, repo_id, version,
        )
        return doc
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.exception(
            "[DOCS-GEN-B-301] DB 저장 실패 | repo_id=%s version=%d: %s",
            repo_id, version, exc,
        )
        raise DatabaseSaveFailedError() from exc
