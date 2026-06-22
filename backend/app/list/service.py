import os
from dataclasses import dataclass
from typing import Annotated, Optional
from uuid import UUID

import httpx
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.config import get_settings
from app.core.exceptions import (
    CodeMapException,
    InvalidRepoUrlError,
    RepositoryNotFoundError,
    ValidationFailedError,
)
from app.list.models import AnalysisJobDetailModel, AnalysisJobListModel
from app.list.repository import AnalysisJobListRepository
from app.list.schemas import PreValidateData, PreValidateResponse
from app.repo.service import (
    EXCLUDED_DIRS,
    EXCLUDED_FILE_EXTENSIONS,
    EXCLUDED_FILE_NAMES,
    GITHUB_URL_PATTERN,
)


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


    # ──────────────────────────────────────────────
    # validate_repository
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
        if not target_branch:
            api_url = f"https://api.github.com/repos/{owner}/{repo_name}"
            try:
                async with httpx.AsyncClient(timeout=5) as client:
                    response = await client.get(
                        api_url,
                        headers=headers,
                    )
                if response.status_code == 404:
                    raise RepositoryNotFoundError("저장소가 없거나 접근할 수 없습니다.")
                if response.status_code >= 400:
                    raise ValidationFailedError(
                        f"GitHub API 호출 중 오류가 발생했습니다: HTTP {response.status_code}"
                    )
                payload = response.json()
                target_branch = payload.get("default_branch", "main")
            except RepositoryNotFoundError:
                raise
            except CodeMapException:
                raise
            except Exception as exc:
                raise ValidationFailedError(f"GitHub API 호출 중 오류가 발생했습니다: {exc}") from exc

        tree_url = f"https://api.github.com/repos/{owner}/{repo_name}/git/trees/{target_branch}?recursive=1"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(
                    tree_url,
                    headers=headers,
                )
            if response.status_code == 404:
                raise RepositoryNotFoundError("지정한 브랜치 또는 저장소를 찾을 수 없습니다.")
            if response.status_code >= 400:
                raise ValidationFailedError(
                    f"GitHub API 호출 중 오류가 발생했습니다: HTTP {response.status_code}"
                )
            payload = response.json()
        except RepositoryNotFoundError:
            raise
        except CodeMapException:
            raise
        except Exception as exc:
            raise ValidationFailedError(f"GitHub API 호출 중 오류가 발생했습니다: {exc}") from exc

        tree = payload.get("tree", [])
        file_count = 0
        total_size = 0
        any_file_exceeds_100kb = False

        for item in tree:
            if item.get("type") == "blob":
                path = item.get("path", "")
                if _should_exclude_path(path):
                    continue

                file_count += 1
                size = item.get("size", 0)
                total_size += size
                if size > 100 * 1024:
                    any_file_exceeds_100kb = True

        total_size_kb = (total_size + 1023) // 1024
        is_valid = (file_count <= 100) and (not any_file_exceeds_100kb)

        warning_message = None
        if file_count > 100:
            warning_message = "저장소 파일 수가 100개를 초과합니다. 분석 시 가장 핵심이 되는 100개의 파일만 지능적으로 자동 선택되어 분석이 진행됩니다."
        elif any_file_exceeds_100kb:
            warning_message = "100KB를 초과하는 대용량 파일이 존재합니다. 해당 파일은 분석 대상에서 제외되거나 제한적으로 분석될 수 있습니다."

        return PreValidateResponse(
            code=200,
            message="success",
            data=PreValidateData(
                is_valid=is_valid,
                file_count=file_count,
                total_size_kb=total_size_kb,
                warning_message=warning_message,
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

    binary_extensions = {
        ".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".pdf",
        ".zip", ".tar", ".gz", ".rar", ".7z", ".exe", ".dll",
        ".so", ".dylib", ".class", ".pyc", ".db", ".sqlite",
        ".woff", ".woff2", ".ttf", ".eot", ".mp3", ".mp4",
    }
    if ext_lower in binary_extensions:
        return True

    return False


def get_list_service(db: Annotated[AsyncSession, Depends(get_db)]) -> ListService:
    """FastAPI 의존성 주입으로 ListService 인스턴스를 생성합니다."""
    return ListService(db)


# 의존성 주입 타입 별칭은 파일 하단에 모아 관리합니다.
ListserviceDep = Annotated[ListService, Depends(get_list_service)]
