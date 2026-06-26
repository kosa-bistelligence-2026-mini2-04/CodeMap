import os
import logging
from dataclasses import dataclass
from typing import Annotated, Optional
from urllib.parse import quote as url_quote
from uuid import UUID

import httpx
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.database import get_db
from app.list.models import (
    AnalysisJobDetailModel,
    AnalysisJobListModel,
    AnalysisJobStatusUpdateModel,
)
from app.infra.config import get_settings
from app.common.exceptions import (
    CodeMapException,
    InvalidRepoUrlError,
    RepositoryNotFoundError,
    ValidationFailedError,
)
from app.list.repository import AnalysisJobListRepository
from app.list.schemas import PreValidateData, PreValidateResponse, PreValidateLimit
from app.repo.service import (
    EXCLUDED_DIRS,
    EXCLUDED_FILE_EXTENSIONS,
    EXCLUDED_FILE_NAMES,
    GITHUB_URL_PATTERN,
)

BINARY_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".pdf",
    ".zip", ".tar", ".gz", ".rar", ".7z", ".exe", ".dll",
    ".so", ".dylib", ".class", ".pyc", ".db", ".sqlite",
    ".woff", ".woff2", ".ttf", ".eot", ".mp3", ".mp4",
}


logger = logging.getLogger(__name__)


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

    async def delete_job(self, job_id: UUID) -> bool:
        """분석 이력을 삭제합니다."""
        return await self.repository.delete_job(job_id)

    def _to_db_status(self, status: str) -> str:
        """API 상태값을 DB 저장 상태값으로 변환합니다."""
        status_map = {
            "queued": "CLONED",
            "running": "IN_PROGRESS",
            "completed": "COMPLETED",
            "failed": "FAILED",
        }
        return status_map[status]


    # ──────────────────────────────────────────────
    # validate_repository 메서드 정의
    # ──────────────────────────────────────────────
    async def validate_repository(
        self,
        repo_url: str,
        branch: Optional[str] = None,
    ) -> PreValidateResponse:
        """
        본격 분석 시작 전 GitHub 저장소의 파일 개수와 크기를 사전 검증합니다.
        """
        match = GITHUB_URL_PATTERN.match(repo_url.strip())
        if not match:
            raise InvalidRepoUrlError(f"올바른 GitHub URL 형식이 아닙니다: {repo_url}")

        owner = match.group("owner")
        repo_name = match.group("repo")

        ## GitHub API 공통 헤더 구성 (인증 토큰 적용)
        settings = get_settings()
        headers = {"User-Agent": "CodeMap"}
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

        target_branch = branch

        try:
            ## 이슈 #3 수정: AsyncClient를 1개로 통합하여 커넥션 재사용
            async with httpx.AsyncClient(timeout=10, headers=headers) as client:
                if not target_branch:
                    ## default_branch 확인
                    api_url = f"https://api.github.com/repos/{owner}/{repo_name}"
                    response = await client.get(api_url)
                    if response.status_code == 404:
                        raise RepositoryNotFoundError("저장소가 없거나 접근할 수 없습니다.")
                    if response.status_code >= 400:
                        raise ValidationFailedError(
                            f"GitHub API 호출 중 오류가 발생했습니다: HTTP {response.status_code}"
                        )
                    try:
                        repo_info = response.json()
                        if not isinstance(repo_info, dict):
                            raise ValidationFailedError("API 응답 형식이 올바르지 않습니다.")
                        target_branch = repo_info.get("default_branch")
                        if not target_branch:
                            raise ValidationFailedError("저장소 정보에서 기본 브랜치(default_branch)를 찾을 수 없습니다.")
                    except (ValueError, TypeError) as exc:
                        raise ValidationFailedError(f"저장소 정보 파싱 중 오류가 발생했습니다: {exc}")

                ## 이슈 #별도 제안: 브랜치명 URL encoding (슬래시 등 특수문자 대응)
                encoded_branch = url_quote(target_branch, safe="")
                tree_url = (
                    f"https://api.github.com/repos/{owner}/{repo_name}"
                    f"/git/trees/{encoded_branch}?recursive=1"
                )
                tree_response = await client.get(tree_url)

            if tree_response.status_code == 404:
                raise RepositoryNotFoundError("지정한 브랜치 또는 저장소를 찾을 수 없습니다.")
            if tree_response.status_code >= 400:
                raise ValidationFailedError(
                    f"GitHub API 호출 중 오류가 발생했습니다: HTTP {tree_response.status_code}"
                )
            payload = tree_response.json()
        except RepositoryNotFoundError:
            raise
        except CodeMapException:
            raise
        except Exception as exc:
            logger.exception("GitHub 저장소 사전 검증 중 예상치 못한 오류 발생", exc_info=exc)
            raise ValidationFailedError("GitHub 저장소 정보를 가져오는 중 서버 오류가 발생했습니다.") from exc

        # API-005 스펙 준수: 제한 기준 설정값 DTO 상시 반환용 기본 인스턴스 생성
        limit = PreValidateLimit(fileCount=100, fileSizeKb=100)

        ## 이슈 #별도 제안: truncated 응답 처리
        ## GitHub Trees API는 큼 저장소에서 truncated=true를 내립니다.
        ## 이 경우 실제 파일 수/용량보다 적게 계산되어 isValid=true를 잘못 반환할 수 있습니다.
        if payload.get("truncated", False):
            return PreValidateResponse(
                code=200,
                message="success",
                data=PreValidateData(
                    is_valid=False,
                    file_count=0,
                    total_size_kb=0,
                    warning_message="저장소가 너무 커서 GitHub API가 파일 목록을 누락(truncated)했습니다. 세부 파일 필터링 없이 전체 분석이 불가능합니다.",
                    is_truncated=True,
                    limit=limit,
                ),
            )

        tree = payload.get("tree", [])
        file_count = 0
        total_size = 0
        max_file_size = 0
        any_file_exceeds_100kb = False

        for item in tree:
            if item.get("type") == "blob":
                path = item.get("path", "")
                if _should_exclude_path(path):
                    continue

                size = item.get("size")
                if size is None:
                    # size 정보가 없는 blob(예: 서브모듈)은 파일 수 및 용량 집계에서 제외
                    continue

                file_count += 1
                total_size += size
                max_file_size = max(max_file_size, size)
                if size > 100 * 1024:
                    any_file_exceeds_100kb = True

        total_size_kb = (total_size + 1023) // 1024
        max_file_size_kb = (max_file_size + 1023) // 1024 if max_file_size > 0 else 0

        if file_count == 0:
            raise ValidationFailedError("저장소 내에 분석 가능한 파일이 없습니다.")

        ## 이슈 #4 수정: warning_message를 먼저 생성하고 is_valid는 단일 소스로 통일
        warning_message = None
        warning_code = None

        if file_count > 100 and any_file_exceeds_100kb:
            warning_message = "저장소 파일 수와 개별 파일 용량 제한을 모두 초과하였습니다. 핵심 파일만 선별하여 분석을 진행해야 합니다."
            warning_code = "REPO_LIMIT_EXCEEDED"
        elif file_count > 100:
            warning_message = "저장소 파일 수가 100개를 초과합니다. 핵심 파일만 선별하여 분석을 진행해야 합니다."
            warning_code = "FILE_COUNT_EXCEEDED"
        elif any_file_exceeds_100kb:
            warning_message = "100KB를 초과하는 대용량 파일이 존재합니다. 해당 파일은 분석 대상에서 제외되거나 제한적으로 분석될 수 있습니다."
            warning_code = "FILE_SIZE_EXCEEDED"

        is_valid = warning_message is None

        return PreValidateResponse(
            code=200,
            message="success",
            data=PreValidateData(
                is_valid=is_valid,
                file_count=file_count,
                total_size_kb=total_size_kb,
                warning_message=warning_message,
                is_truncated=False,
                warning_code=warning_code,
                max_file_size_kb=max_file_size_kb,
                limit=limit,
            ),
        )


# ──────────────────────────────────────────────
# _should_exclude_path
# ──────────────────────────────────────────────
def _should_exclude_path(path: str) -> bool:
    """
    제시된 경로가 제외 디렉토리/파일 명세 및 바이너리 패턴에 해당하는지 확인합니다.
    """
    parts = path.split("/")
    for part in parts[:-1]:
        if part in EXCLUDED_DIRS:
            return True

    filename = parts[-1]
    if filename.lower() in EXCLUDED_FILE_NAMES:
        return True

    _, ext = os.path.splitext(filename)
    ext_lower = ext.lower()
    if ext_lower in EXCLUDED_FILE_EXTENSIONS:
        return True

    if ext_lower in BINARY_EXTENSIONS:
        return True

    return False


def get_list_service(db: Annotated[AsyncSession, Depends(get_db)]) -> ListService:
    """FastAPI 의존성 주입으로 ListService 인스턴스를 생성합니다."""
    return ListService(db)


# 의존성 주입 타입 별칭은 파일 하단에 모아 관리합니다.
ListServiceDep = Annotated[ListService, Depends(get_list_service)]
