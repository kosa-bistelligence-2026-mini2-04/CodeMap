from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.list.models import AnalysisJobListModel
from app.list.repository import AnalysisJobListRepository


@dataclass
class AnalysisJobListResult:
    """라우터가 응답 DTO로 변환하기 전 사용하는 서비스 결과입니다."""

    total_count: int
    page: int
    limit: int
    jobs: list[AnalysisJobListModel]


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


def get_list_service(db: Annotated[AsyncSession, Depends(get_db)]) -> ListService:
    """FastAPI 의존성 주입으로 ListService 인스턴스를 생성합니다."""
    return ListService(db)


# 의존성 주입 타입 별칭은 파일 하단에 모아 관리합니다.
ListserviceDep = Annotated[ListService, Depends(get_list_service)]
