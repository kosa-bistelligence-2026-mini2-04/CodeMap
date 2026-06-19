import logging
from dataclasses import dataclass
from typing import Annotated, Optional

import giturlparse
import httpx
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from tenacity import retry, stop_after_attempt, wait_fixed, retry_if_exception_type

from app.core.config import get_settings
from app.core.database import get_db
from app.core.exceptions import InvalidRepoUrlError, RepositoryNotFoundError, ValidationFailedError
from app.list.models import AnalysisJobListModel
from app.list.repository import AnalysisJobListRepository
from app.list.schemas import ListValidateData

logger = logging.getLogger(__name__)
settings = get_settings()
# ======================================================================
# fetch_github_api
# 타임아웃 발생 시 최대 3회 재시도하며 GitHub API를 비동기로 호출합니다.
# ======================================================================
@retry(
    retry=retry_if_exception_type(httpx.TimeoutException),
    stop=stop_after_attempt(3),
    wait=wait_fixed(2),
    reraise=True
)
async def fetch_github_api(client: httpx.AsyncClient, url: str, headers: dict) -> httpx.Response:
    '''
    타임아웃 발생 시 최대 3회 재시도하며 GitHub API를 비동기로 호출합니다.
    '''
    try:
        response = await client.get(url, headers=headers, timeout=10.0)
        return response
    except httpx.TimeoutException as exc:
        logger.warning(f"GitHub API 호출 타임아웃 발생. 재시도합니다... ({exc})")
        raise


@dataclass
class AnalysisJobListResult:
    '''라우터가 응답 DTO로 변환하기 전 사용하는 서비스 결과입니다.'''

    total_count: int
    page: int
    limit: int
    jobs: list[AnalysisJobListModel]


class ListService:
    '''프로젝트 분석 이력 목록 조회 및 사전 검증 비즈니스 로직을 담당합니다.'''

    def __init__(self, db: AsyncSession):
        self.repository = AnalysisJobListRepository(db)

    async def get_analysis_jobs(self, page: int, limit: int) -> AnalysisJobListResult:
        '''전체 건수와 현재 페이지의 분석 작업 목록을 함께 반환합니다.'''
        total_count = await self.repository.count_analysis_jobs()
        jobs = await self.repository.find_analysis_jobs(page=page, limit=limit)
        return AnalysisJobListResult(
            total_count=total_count,
            page=page,
            limit=limit,
            jobs=jobs,
        )


    # ======================================================================
    # validate_repository
    # GitHub 저장소의 파일 개수 및 총 크기를 사전 검증합니다.
    # ======================================================================
    async def validate_repository(self, repo_url: str, branch: Optional[str] = None) -> ListValidateData:
        '''
        GitHub 저장소의 파일 개수 및 총 크기를 사전 검증합니다.
        '''

        # ===
        # URL 파싱 수행
        # ===
        try:
            parsed = giturlparse.parse(repo_url)
            if not parsed.valid or not parsed.owner or not parsed.repo:
                raise InvalidRepoUrlError()
            owner = parsed.owner
            repo = parsed.repo
        except Exception as exc:
            logger.error(f"URL 파싱 에러: {exc}")
            raise InvalidRepoUrlError()

        headers = {"Accept": "application/vnd.github+json"}
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

        async with httpx.AsyncClient() as client:
            # ===
            # 디폴트 브랜치 획득 (branch가 제공되지 않은 경우)
            # ===
            if not branch:
                repo_info_url = f"https://api.github.com/repos/{owner}/{repo}"
                try:
                    ## tenacity retry 데코레이터가 적용된 헬퍼 호출
                    response = await fetch_github_api(client, repo_info_url, headers)

                    if response.status_code == 404:
                        raise RepositoryNotFoundError()
                    elif response.status_code == 403:
                        ## 권한 없음 에러 처리
                        raise RepositoryNotFoundError("저장소가 존재하지 않거나 프라이빗 저장소로 접근 권한이 없습니다.")
                    elif response.status_code != 200:
                        raise ValidationFailedError(message=f"저장소 정보 획득 실패 (Status: {response.status_code})")

                    repo_data = response.json()
                    branch = repo_data.get("default_branch", "main")
                except httpx.TimeoutException as exc:
                    ## 3회 재시도 모두 타임아웃 실패 시 응답 사양 처리
                    logger.error(f"지속적인 깃허브 API 타임아웃으로 실패: {exc}")
                    error_msg = "깃허브 API 호출 시간 초과(3회 재시도 실패). 네트워크 상태를 확인하시거나 나중에 다시 시도해 주십시오."
                    raise ValidationFailedError(message=error_msg)

            # ===
            # Git Trees API 재귀 조회
            # ===
            trees_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
            try:
                response = await fetch_github_api(client, trees_url, headers)

                ## 409 Conflict 빈 저장소 예외 Hooking
                if response.status_code == 409:
                    logger.warning("빈 저장소 감지 (409 Conflict). 검증을 통과 처리합니다.")
                    return ListValidateData(
                        isValid=True,
                        fileCount=0,
                        totalSizeKb=0.0,
                        warningMessage="빈 저장소입니다. 분석을 위한 소스 파일이 존재하지 않습니다."
                    )
                elif response.status_code == 404:
                    raise RepositoryNotFoundError()
                elif response.status_code != 200:
                    raise ValidationFailedError(message=f"저장소 파일 목록 조회 실패 (Status: {response.status_code})")

                tree_data = response.json()
            except httpx.TimeoutException as exc:
                logger.error(f"지속적인 깃허브 API 타임아웃으로 실패: {exc}")
                error_msg = "깃허브 API 호출 시간 초과(3회 재시도 실패). 네트워크 상태를 확인하시거나 나중에 다시 시도해 주십시오."
                raise ValidationFailedError(message=error_msg)

            # ===
            # 트리 결과 분석 및 용량 산출
            # ===
            ## truncated 결과 처리
            if tree_data.get("truncated") is True:
                logger.warning("저장소 트리가 초과되어 truncated 됨 (10만개 초과)")
                return ListValidateData(
                    isValid=False,
                    fileCount=100000,
                    totalSizeKb=500000.0,
                    warningMessage="저장소 크기가 제한 한도를 크게 초과하여 데이터가 잘렸습니다. 분석 대상 파일을 지능적으로 선별합니다."
                )

            tree_items = tree_data.get("tree", [])
            file_count = 0
            total_size_bytes = 0

            for item in tree_items:
                if item.get("type") == "blob":
                    file_count += 1
                    total_size_bytes += item.get("size", 0)

            total_size_kb = round(total_size_bytes / 1024, 2)

            # ===
            # 제한 조건 판정 (기준: 300개)
            # ===
            if file_count <= 300:
                return ListValidateData(
                    isValid=True,
                    fileCount=file_count,
                    totalSizeKb=total_size_kb,
                    warningMessage=None
                )
            else:
                warning_msg = "저장소 파일 수가 300개를 초과합니다. 분석 시 가장 핵심이 되는 100개의 파일만 지능적으로 자동 선택되어 분석이 진행됩니다."
                return ListValidateData(
                    isValid=False,
                    fileCount=file_count,
                    totalSizeKb=total_size_kb,
                    warningMessage=warning_msg
                )


def get_list_service(db: Annotated[AsyncSession, Depends(get_db)]) -> ListService:
    '''FastAPI 의존성 주입으로 ListService 인스턴스를 생성합니다.'''
    return ListService(db)


## 의존성 주입 타입 별칭은 파일 하단에 모아 관리합니다.
ListserviceDep = Annotated[ListService, Depends(get_list_service)]
