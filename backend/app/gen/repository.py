"""
DOCS-GEN 데이터 접근 계층 (Repository)

OnboardingDoc 엔티티에 대한 CRUD DB 작업을 수행한다.
commit은 호출측 service에서 담당한다.
"""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.gen.models import OnboardingDoc
from app.repo.models import AnalysisJob

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
# DOCS-GEN Repository 클래스
# ──────────────────────────────────────────────
class GenDocRepository:
    '''
    OnboardingDoc 테이블에 대한 데이터 접근 계층

    모든 메서드는 외부에서 주입받은 AsyncSession을 통해 실행한다.
    commit은 호출측(service)에서 담당한다.
    '''

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ──────────────────────────────────────────
    # 저장소 존재 여부 확인
    # ──────────────────────────────────────────
    async def get_repo_by_id(self, repo_id: UUID) -> AnalysisJob | None:
        '''
        repo_id에 해당하는 AnalysisJob 레코드를 조회한다.

        Returns:
            AnalysisJob 또는 None (존재하지 않을 때)
        '''
        result = await self.db.execute(
            select(AnalysisJob).where(AnalysisJob.id == repo_id)
        )
        return result.scalar_one_or_none()

    # ──────────────────────────────────────────
    # 문서 저장 (INSERT)
    # ──────────────────────────────────────────
    async def save_doc(
        self,
        repo_id: UUID,
        job_id: UUID,
        content: str,
        version: int,
        doc_type: str = "onboarding",
        report_json: dict | None = None,
    ) -> OnboardingDoc:
        '''
        온보딩 가이드북 Markdown을 docs 테이블에 저장한다.

        Args:
            repo_id:     대상 저장소 ID (analysis_jobs.id)
            job_id:      문서 생성을 트리거한 분석 작업 ID
            content:     저장할 Markdown 가이드북 전문
            version:     가이드북 버전 번호
            doc_type:    문서 유형 (기본: "onboarding")
            report_json: master_report JSON 원본 (format=json 응답용, 선택)

        Returns:
            저장된 OnboardingDoc 엔티티
        '''
        doc = OnboardingDoc(
            repo_id=repo_id,
            job_id=job_id,
            doc_type=doc_type,
            content=content,
            version=version,
            report_json=report_json,
        )
        self.db.add(doc)
        await self.db.flush()
        logger.info(
            "[GenDocRepository] 문서 저장 완료 | doc_id=%s repo_id=%s version=%d",
            doc.id, repo_id, version,
        )
        return doc

    # ──────────────────────────────────────────
    # 활성 문서 조회 (API-001)
    # ──────────────────────────────────────────
    async def get_active_by_repo_id(self, repo_id: UUID) -> OnboardingDoc | None:
        '''
        해당 저장소의 활성 온보딩 가이드북 최신 버전을 반환한다.

        Returns:
            활성 OnboardingDoc 또는 None (없으면)
        '''
        result = await self.db.execute(
            select(OnboardingDoc)
            .where(OnboardingDoc.repo_id == repo_id)
            .where(OnboardingDoc.is_active.is_(True))
            .order_by(OnboardingDoc.version.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    # ──────────────────────────────────────────
    # 최신 버전 번호 조회
    # ──────────────────────────────────────────
    async def get_latest_version(self, repo_id: UUID) -> int:
        '''
        해당 저장소의 최신 가이드북 버전 번호를 반환한다.
        문서가 없으면 0을 반환한다.

        Returns:
            최신 버전 번호 (문서 없으면 0)
        '''
        result = await self.db.execute(
            select(OnboardingDoc.version)
            .where(OnboardingDoc.repo_id == repo_id)
            .order_by(OnboardingDoc.version.desc())
            .limit(1)
        )
        version = result.scalar_one_or_none()
        return version if version is not None else 0
