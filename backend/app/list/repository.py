from datetime import datetime, timezone
from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import defer
from sqlalchemy.ext.asyncio import AsyncSession

from uuid import UUID

from app.list.models import (
    AnalysisJobDetailModel,
    AnalysisJobListModel,
    AnalysisJobStatusUpdateModel,
)
from app.repo.models import AnalysisJob
from app.auth.models import TeamMember
from app.common import access


class AnalysisJobListRepository:
    """분석 작업 목록 조회에 필요한 DB 접근을 담당합니다."""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _access_filter(
        self,
        current_user_id: UUID | None,
        scope: str = "all",
        team_id: UUID | None = None,
    ):
        if current_user_id is None:
            return and_(
                AnalysisJob.user_id.is_(None),
                AnalysisJob.team_id.is_(None),
                AnalysisJob.is_private == False,
            )

        private_filter = and_(
            AnalysisJob.team_id.is_(None),
            AnalysisJob.user_id == current_user_id,
        )
        team_filter = and_(
            AnalysisJob.team_id.is_not(None),
            exists().where(
                TeamMember.team_id == AnalysisJob.team_id,
                TeamMember.user_id == current_user_id,
                TeamMember.status == "active",
            ),
        )
        if team_id is not None:
            team_filter = and_(team_filter, AnalysisJob.team_id == team_id)
        if scope == "private":
            return private_filter
        if scope == "team":
            return team_filter
        return or_(private_filter, team_filter)

    async def count_analysis_jobs(
        self,
        current_user_id: UUID | None = None,
        scope: str = "all",
        team_id: UUID | None = None,
    ) -> int:
        """접근 가능한 분석 작업 수를 조회합니다.

        Private job은 소유자만 카운트에 포함됩니다.
        """
        result = await self.db.execute(
            select(func.count()).select_from(AnalysisJob).where(
                self._access_filter(current_user_id, scope=scope, team_id=team_id)
            )
        )
        return result.scalar_one()

    async def find_analysis_jobs(
        self,
        page: int,
        limit: int,
        current_user_id: UUID | None = None,
        scope: str = "all",
        team_id: UUID | None = None,
    ) -> list[AnalysisJobListModel]:
        """페이지 번호와 페이지 크기에 맞춰 분석 작업 목록을 조회합니다.

        Private job은 소유자만 조회됩니다.
        """
        offset = (page - 1) * limit
        result = await self.db.execute(
            select(AnalysisJob)
            .options(defer(AnalysisJob.report_json))
            .where(self._access_filter(current_user_id, scope=scope, team_id=team_id))
            .order_by(AnalysisJob.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        return [self._to_list_model(job) for job in result.scalars().all()]

    async def find_analysis_job_detail(
        self,
        job_id: UUID,
        current_user_id: UUID | None = None,
    ) -> AnalysisJobDetailModel | None:
        """분석 작업 고유 ID로 상세 정보를 조회합니다.

        Private job은 소유자만 조회할 수 있으며, 그 외에는 None을 반환합니다.
        """
        result = await self.db.execute(select(AnalysisJob).where(AnalysisJob.id == job_id))
        job = result.scalar_one_or_none()
        if job is None:
            return None
        if not await self.can_access_job(job, current_user_id):
            return None
        return self._to_detail_model(job)

    async def can_access_job(
        self,
        job: AnalysisJob,
        current_user_id: UUID | None,
    ) -> bool:
        ## 단일 판정 모듈에 위임 (자체 PR 리뷰 M3)
        return await access.can_access_job(self.db, job, current_user_id)

    async def update_analysis_job_status(
        self,
        job_id: UUID,
        status: str,
        current_step: str | None,
        progress: int,
        message: str | None,
    ) -> AnalysisJobStatusUpdateModel | None:
        """분석 작업 상태와 진행 정보를 저장합니다."""
        result = await self.db.execute(select(AnalysisJob).where(AnalysisJob.id == job_id))
        job = result.scalar_one_or_none()
        if job is None:
            return None

        job.status = status
        job.stage = current_step
        job.progress = progress
        job.message = message
        job.updated_at = datetime.now(timezone.utc)

        await self.db.commit()
        await self.db.refresh(job)
        return self._to_status_update_model(job)

    async def delete_job(self, job_id: UUID, current_user_id: UUID) -> bool:
        """분석 작업 엔티티를 삭제합니다."""
        stmt = select(AnalysisJob).where(AnalysisJob.id == job_id)
        result = await self.db.execute(stmt)
        job = result.scalar_one_or_none()
        if job:
            user_id = getattr(job, "user_id", None)
            if user_id is not None and user_id != current_user_id:
                return False
            
            await self.db.delete(job)
            await self.db.commit()
            return True
        return False

    def _to_list_model(self, job: AnalysisJob) -> AnalysisJobListModel:
        """DB 엔티티를 목록 API 내부 모델로 변환합니다."""
        is_failed = job.status == "FAILED"
        return AnalysisJobListModel(
            job_id=job.id,
            repo_url=job.repo_url,
            branch=job.branch,
            status=self._to_api_status(job.status),
            progress=job.progress,
            failed_agent=job.stage if is_failed else None,
            error_message=job.message if is_failed else None,
            visibility="team" if job.team_id is not None else "private",
            team_id=job.team_id,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    def _to_detail_model(self, job: AnalysisJob) -> AnalysisJobDetailModel:
        """DB 엔티티를 상세 조회 API 내부 모델로 변환합니다."""
        return AnalysisJobDetailModel(
            job_id=job.id,
            repo_url=job.repo_url,
            repo_name=job.repo_name,
            owner=job.owner,
            branch=job.branch,
            status=self._to_api_status(job.status),
            current_step=job.stage,
            progress=job.progress,
            message=job.message,
            visibility="team" if job.team_id is not None else "private",
            team_id=job.team_id,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    def _to_status_update_model(self, job: AnalysisJob) -> AnalysisJobStatusUpdateModel:
        """DB 엔티티를 상태 저장 API 내부 모델로 변환합니다."""
        return AnalysisJobStatusUpdateModel(
            job_id=job.id,
            status=self._to_api_status(job.status),
            current_step=job.stage,
            progress=job.progress,
            updated_at=job.updated_at,
        )

    def _to_api_status(self, status: str) -> str:
        """DB 작업 상태를 명세의 응답 상태값으로 변환합니다."""
        status_map = {
            "CLONED": "queued",
            "IN_PROGRESS": "running",
            "COMPLETED": "completed",
            "FAILED": "failed",
        }
        return status_map.get(status, status.lower())
