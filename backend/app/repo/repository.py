"""
분석 작업 데이터 접근 계층 (Repository/DAO)

AnalysisJob 엔티티에 대한 CRUD 데이터베이스 작업을 수행한다.
Service 계층에서 호출되며, SQL 쿼리 로직을 캡슐화한다.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.exceptions import AlreadyInProgressError
from app.common import access
from app.auth.models import TeamMember

from app.repo.models import AnalysisJob
from app.repo.schemas import JobStatus


# ──────────────────────────────────────────────
# 분석 작업 Repository 클래스
# ──────────────────────────────────────────────
class AnalysisJobRepository:
    """
    AnalysisJob 테이블에 대한 데이터 접근 계층

    모든 메서드는 AsyncSession을 주입받아 비동기 DB 작업을 수행한다.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    # ──────────────────────────────────────────
    # 새 분석 작업 생성 (INSERT)
    # ──────────────────────────────────────────
    async def create_job(
        self,
        repo_url: str,
        repo_name: str,
        owner: str,
        branch: str,
        model_used: str = "auto",
        force_refresh: bool = False,
        user_id: UUID | None = None,
        is_private: bool = False,
        team_id: UUID | None = None,
    ) -> AnalysisJob:
        """
        새로운 분석 작업 레코드를 DB에 생성한다.

        Args:
            repo_url: GitHub 저장소 전체 URL
            repo_name: 저장소 이름
            owner: 저장소 소유자
            branch: 분석 대상 브랜치

        Returns:
            생성된 AnalysisJob 엔티티
        """
        job = AnalysisJob(
            repo_url=repo_url,
            repo_name=repo_name,
            owner=owner,
            branch=branch,
            status=JobStatus.IN_PROGRESS.value,
            stage=None,
            model_used=model_used,
            force_refresh=force_refresh,
            user_id=user_id,
            is_private=is_private,
            team_id=team_id,
            progress=0,
            message="분석 작업이 등록되었습니다.",

        )
        self.db.add(job) # DB에 INSERT 준비
        try:
            await self.db.flush() # SQL 실행 (아직 commit은 아님)
        except IntegrityError as exc:
            await self.db.rollback()
            if exc.orig and "uq_analysis_jobs_in_progress" in str(exc.orig):
                raise AlreadyInProgressError()
            raise
        await self.db.refresh(job) # 자동생성된 id, created_at 등 다시 읽어오기
        return job

    # ──────────────────────────────────────────
    # job_id로 분석 작업 조회 (SELECT)
    # ──────────────────────────────────────────
    async def get_job_by_id(self, job_id: UUID) -> Optional[AnalysisJob]:
        """
        job_id로 분석 작업을 조회한다.

        Args:
            job_id: 분석 작업 고유 ID

        Returns:
            AnalysisJob 엔티티 또는 None (존재하지 않는 경우)
        """
        result = await self.db.execute(
            select(AnalysisJob).where(AnalysisJob.id == job_id)
        )
        return result.scalar_one_or_none()

    # ──────────────────────────────────────────
    # 동일 저장소 중복 분석 확인 (SELECT)
    # ──────────────────────────────────────────
    async def check_duplicate_job(
        self,
        repo_url: str,
        branch: str,
        user_id: UUID | None = None,
        team_id: UUID | None = None,
    ) -> Optional[AnalysisJob]:
        """
        동일한 저장소 URL과 브랜치에 대해 이미 진행 중인 분석 작업이 있는지 확인한다.

        Args:
            repo_url: GitHub 저장소 URL
            branch: 분석 대상 브랜치

        Returns:
            진행 중인 AnalysisJob 엔티티 또는 None
        """
        stmt = select(AnalysisJob).where(
            AnalysisJob.repo_url == repo_url,
            AnalysisJob.branch == branch,
            AnalysisJob.status.in_([JobStatus.IN_PROGRESS.value, JobStatus.COMPLETED.value]),
        )
        if team_id is not None:
            stmt = stmt.where(AnalysisJob.team_id == team_id)
        elif user_id is not None:
            stmt = stmt.where(AnalysisJob.user_id == user_id, AnalysisJob.team_id.is_(None))
        else:
            stmt = stmt.where(AnalysisJob.user_id.is_(None), AnalysisJob.team_id.is_(None))
        result = await self.db.execute(
            stmt.order_by(AnalysisJob.created_at.desc()).limit(1)
        )
        return result.scalar_one_or_none()

    async def user_has_team_access(self, team_id: UUID, user_id: UUID) -> bool:
        ## 단일 판정 모듈에 위임 (자체 PR 리뷰 M3)
        return await access.user_has_team_access(self.db, team_id, user_id)

    async def list_jobs(self, limit: int = 30) -> list[AnalysisJob]:
        result = await self.db.execute(
            select(AnalysisJob).order_by(AnalysisJob.created_at.desc()).limit(min(limit, 100))
        )
        return list(result.scalars())

    # ──────────────────────────────────────────
    # 분석 작업 상태 업데이트 (UPDATE)
    # ──────────────────────────────────────────
    async def update_job_status(
        self,
        job_id: UUID,
        status: str,
        stage: Optional[str] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        report_json: Optional[dict] = None,
    ) -> Optional[AnalysisJob]:
        """
        분석 작업의 상태를 업데이트한다.

        파이프라인 진행에 따라 status, stage, progress, message 등을 갱신한다.
        clone_path는 job_id + CLONE_BASE_DIR config로 항상 계산 가능하므로 저장하지 않는다.

        Args:
            job_id: 분석 작업 고유 ID
            status: 변경할 상태 값
            stage: 현재 파이프라인 단계
            progress: 전체 진행률 (0~100)
            message: 진행 상태 메시지

        Returns:
            업데이트된 AnalysisJob 엔티티 또는 None
        """
        job = await self.get_job_by_id(job_id)
        if not job:
            return None

        job.status = status
        job.updated_at = datetime.now(timezone.utc)

        if stage is not None:
            job.stage = stage
        if progress is not None:
            job.progress = progress
        if message is not None:
            job.message = message
        if report_json is not None:
            job.report_json = report_json

        await self.db.flush()
        await self.db.refresh(job)
        return job
