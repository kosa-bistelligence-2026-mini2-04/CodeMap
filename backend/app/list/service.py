from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.list.models import (
    AnalysisJobDetailModel,
    AnalysisJobListModel,
    AnalysisJobStatusUpdateModel,
)
from app.list.repository import AnalysisJobListRepository


@dataclass
class AnalysisJobListResult:
    """라우터가 응답 DTO로 변환하기 전 사용하는 서비스 결과입니다."""

    total_count: int
    page: int
    limit: int
    jobs: list[AnalysisJobListModel]


@dataclass
class AnalysisJobDetailResult:
    """라우터가 상세 응답 DTO로 변환하기 전에 사용하는 서비스 결과입니다."""

    job: AnalysisJobDetailModel | None


@dataclass
class AnalysisJobStatusUpdateResult:
    """라우터가 상태 저장 응답 DTO로 변환하기 전에 사용하는 서비스 결과입니다."""

    job: AnalysisJobStatusUpdateModel | None


class ListService:
    """프로젝트 분석 이력 목록 조회 비즈니스 로직을 담당합니다."""

    def __init__(self, db: AsyncSession):
        self.repository = AnalysisJobListRepository(db)

    async def get_analysis_jobs(self, page: int, limit: int) -> AnalysisJobListResult:
        """전체 건수와 현재 페이지의 분석 작업 목록을 함께 반환합니다."""
        total_count = await self.repository.count_analysis_jobs()
        jobs = await self.repository.find_analysis_jobs(page=page, limit=limit)
        return AnalysisJobListResult(
            total_count=total_count,
            page=page,
            limit=limit,
            jobs=jobs,
        )

    async def get_analysis_job_detail(self, job_id: UUID) -> AnalysisJobDetailResult:
        """특정 분석 작업의 상세 상태와 메타데이터를 조회합니다."""
        job = await self.repository.find_analysis_job_detail(job_id)
        return AnalysisJobDetailResult(job=job)

    async def update_analysis_job_status(
        self,
        job_id: UUID,
        status: str,
        current_step: str | None,
        progress: int,
        message: str | None,
        error_message: str | None,
    ) -> AnalysisJobStatusUpdateResult:
        """상태 저장 명세에 맞춰 작업 상태와 진행 정보를 저장합니다."""
        db_status = self._to_db_status(status)
        stored_message = error_message if status == "failed" and error_message else message
        job = await self.repository.update_analysis_job_status(
            job_id=job_id,
            status=db_status,
            current_step=current_step,
            progress=progress,
            message=stored_message,
        )
        return AnalysisJobStatusUpdateResult(job=job)

    def _to_db_status(self, status: str) -> str:
        """API 상태값을 DB 저장 상태값으로 변환합니다."""
        status_map = {
            "queued": "CLONED",
            "running": "IN_PROGRESS",
            "completed": "COMPLETED",
            "failed": "FAILED",
        }
        return status_map[status]


def get_list_service(db: Annotated[AsyncSession, Depends(get_db)]) -> ListService:
    """FastAPI 의존성 주입으로 ListService 인스턴스를 생성합니다."""
    return ListService(db)


# 의존성 주입 타입 별칭은 파일 하단에 모아 관리합니다.
ListserviceDep = Annotated[ListService, Depends(get_list_service)]
