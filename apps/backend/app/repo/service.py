"""
분석 작업 비즈니스 로직 계층 (Service)

API 명세서에 정의된 비즈니스 규칙을 구현한다.
GitHub URL 파싱, 저장소 검증, 분석 작업 등록,
파이프라인 실행(LangGraph), 이벤트 발행 등 핵심 로직을 담당한다.

파이프라인 실행 방식:
  # [Sec09 - CustomerSupportSupervisor]
  # kosa-langchain-practice/langchain/api/sec09_multi_agent/langgraph/supervisor.py 참고
  # asyncio.create_task()로 백그라운드 실행 후 AnalysisPipelineSupervisor.run()에 위임한다.
"""

import asyncio
import logging
import re
from datetime import datetime, timezone
from uuid import UUID

import httpx
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import (
    AlreadyInProgressError,
    CloneNotCompletedError,
    CodeMapException,
    InvalidRepoUrlError,
    JobNotFoundError,
    PipelineAlreadyRunningError,
    PipelineStartFailedError,
    RepositoryNotFoundError,
)
from app.repo.event_manager import event_manager
from app.repo.models import AnalysisJob
from app.repo.repository import AnalysisJobRepository
from app.repo.schemas import (
    AnalysisData,
    AnalysisRequest,
    AnalysisResponse,
    JobStatus,
    JobStatusData,
    JobStatusResponse,
    PipelineStage,
    PipelineStartData,
    PipelineStartResponse,
    ProgressEvent,
    RepoValidateData,
    RepoValidateRequest,
    RepoValidateResponse,
)

logger = logging.getLogger(__name__)
settings = get_settings()

# GitHub URL 파싱용 정규식 패턴
GITHUB_URL_PATTERN = re.compile(
    r"^https://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?/?$"
)

# 각 파이프라인 단계별 progress 범위 정의
STAGE_PROGRESS_MAP = {
    PipelineStage.CLONE: (0, 20),
    PipelineStage.CODE_MAP: (21, 50),
    PipelineStage.DOC_GEN: (51, 70),
    PipelineStage.ONBOARDING: (71, 90),
    PipelineStage.REPORT: (91, 100),
}


# ──────────────────────────────────────────────
# 분석 작업 서비스 클래스
# ──────────────────────────────────────────────
class AnalysisService:
    """
    분석 작업 비즈니스 로직을 담당하는 서비스 클래스

    router 계층에서 호출되며, repository를 통해 DB에 접근하고
    event_manager를 통해 실시간 이벤트를 발행한다.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repository = AnalysisJobRepository(db)

    # ──────────────────────────────────────────
    # API-001: 프로젝트 등록 (분석 요청)
    # ──────────────────────────────────────────
    async def register_analysis(self, request: AnalysisRequest, background_tasks: BackgroundTasks) -> AnalysisResponse:
        """
        GitHub 저장소 분석 작업을 등록하고 job_id를 발급한다.

        1. URL 파싱 및 검증
        2. 중복 분석 확인
        3. DB에 작업 등록
        4. 백그라운드 파이프라인 시작

        Args:
            request: 분석 요청 DTO (repoUrl, branch)

        Returns:
            AnalysisResponse: 201 Created 응답
        """
        # 1. GitHub URL에서 owner, repo 이름 파싱
        owner, repo_name = self._parse_github_url(request.repoUrl)

        # 2. 브랜치 미입력 시 기본값 main 설정
        branch = request.branch or "main"

        # 3. 동일 저장소(레포)에 대한 중복 분석이 있는지 확인
        duplicate = await self.repository.check_duplicate_job(request.repoUrl, branch)
        if duplicate:
            raise AlreadyInProgressError()

        # 4. DB에 새 분석 작업 생성
        job = await self.repository.create_job(
            repo_url=request.repoUrl,
            repo_name=repo_name,
            owner=owner,
            branch=branch,
        )

        # 5. [Sec09 - supervisor.run()] 백그라운드에서 LangGraph 파이프라인 실행
        #    응답이 전송되고 DB 커밋이 완료된 후 파이프라인이 실행되도록 BackgroundTasks에 등록한다.
        background_tasks.add_task(self._run_pipeline_with_langgraph, str(job.id))

        # 6. 201 Created 응답 DTO 구성
        return AnalysisResponse(
            code=201,
            message="created",
            data=AnalysisData(
                jobId=job.id,
                repoName=job.repo_name,
                owner=job.owner,
                branch=job.branch,
                status=JobStatus.IN_PROGRESS,
                createdAt=job.created_at,
            ),
        )

    # ──────────────────────────────────────────
    # API-003: 분석 작업 상태 및 메타데이터 조회
    # ──────────────────────────────────────────
    async def get_job_status(self, job_id: UUID) -> JobStatusResponse:
        """
        job_id에 해당하는 분석 작업의 현재 상태와 메타데이터를 반환한다.

        Args:
            job_id: 분석 작업 고유 ID

        Returns:
            JobStatusResponse: 200 OK 응답

        Raises:
            JobNotFoundError: 존재하지 않는 job_id
        """
        job = await self.repository.get_job_by_id(job_id)
        if not job:
            raise JobNotFoundError()

        import os
        clone_path = os.path.join(
            settings.CLONE_BASE_DIR, str(job.id), "repo"
        )

        return JobStatusResponse(
            code=200,
            message="success",
            data=JobStatusData(
                jobId=job.id,
                repoName=job.repo_name,
                owner=job.owner,
                branch=job.branch,
                clonePath=clone_path,
                status=JobStatus(job.status),
                createdAt=job.created_at,
                updatedAt=job.updated_at,
            ),
        )

    # ──────────────────────────────────────────
    # API-007: 전체 분석 파이프라인 시작
    # ──────────────────────────────────────────
    async def start_pipeline(self, job_id: UUID, background_tasks: BackgroundTasks) -> PipelineStartResponse:
        """
        Clone이 완료된 job에 대해 전체 분석 파이프라인을 비동기 시작한다.

        주로 POST /api/analysis 내부에서 자동 호출되나,
        clone 실패 후 수동 재시작 시에만 직접 호출한다.

        Args:
            job_id: 분석 작업 고유 ID

        Returns:
            PipelineStartResponse: 202 Accepted 응답

        Raises:
            JobNotFoundError: 존재하지 않는 job_id
            PipelineAlreadyRunningError: 이미 파이프라인 실행 중
            CloneNotCompletedError: clone 미완료 상태
        """
        job = await self.repository.get_job_by_id(job_id)
        if not job:
            raise JobNotFoundError()

        # 이미 파이프라인이 실행 중인지 확인
        if job.status == JobStatus.IN_PROGRESS.value and job.stage is not None:
            raise PipelineAlreadyRunningError()

        # Clone 완료 여부 확인 (DB clone_path 대신 실제 파일 존재로 판단)
        # clone_path는 job_id + CLONE_BASE_DIR로 항상 결정 가능하므로 DB 저장 불필요
        import os
        clone_path = os.path.join(
            settings.CLONE_BASE_DIR, str(job_id), "repo"
        )
        if not os.path.exists(clone_path):
            raise CloneNotCompletedError()

        now = datetime.now(timezone.utc)

        # 파이프라인 상태를 IN_PROGRESS로 업데이트
        await self.repository.update_job_status(
            job_id=job_id,
            status=JobStatus.IN_PROGRESS.value,
            stage=PipelineStage.CODE_MAP.value,
            progress=21,
            message="분석 파이프라인을 시작합니다.",
        )

        # [Sec09 - supervisor.run()] 백그라운드에서 LangGraph 파이프라인 재시작
        #    응답이 전송되고 DB 커밋이 완료된 후 실행되도록 BackgroundTasks에 등록한다.
        background_tasks.add_task(self._run_pipeline_with_langgraph, str(job_id))

        return PipelineStartResponse(
            code=202,
            message="accepted",
            data=PipelineStartData(
                jobId=job.id,
                status=JobStatus.IN_PROGRESS,
                startedAt=now,
            ),
        )

    # ──────────────────────────────────────────
    # GitHub URL 파싱 유틸리티
    # ──────────────────────────────────────────
    @staticmethod
    def _parse_github_url(url: str) -> tuple[str, str]:
        """
        GitHub URL에서 owner와 repo 이름을 추출한다.

        Args:
            url: GitHub 저장소 URL (https://github.com/owner/repo)

        Returns:
            (owner, repo_name) 튜플

        Raises:
            InvalidRepoUrlError: URL 형식이 올바르지 않음
        """
        match = GITHUB_URL_PATTERN.match(url.strip())
        if not match:
            raise InvalidRepoUrlError(
                f"올바른 GitHub URL 형식이 아닙니다: {url}"
            )
        return match.group("owner"), match.group("repo")

    # ──────────────────────────────────────────────────────────────
    # [Sec09 - supervisor.run()] LangGraph 파이프라인 백그라운드 실행
    # kosa-langchain-practice/langchain/api/sec09_multi_agent/langgraph/supervisor.py 참고
    # ──────────────────────────────────────────────────────────────
    async def _run_pipeline_with_langgraph(
        self, job_id: str
    ) -> None:
        """
        LangGraph AnalysisPipelineSupervisor를 사용하여 분석 파이프라인을 실행한다.

        # [Sec09 - supervisor.run()]
        # kosa-langchain-practice/langchain/api/sec09_multi_agent/langgraph/supervisor.py 참고
        # CustomerSupportSupervisor.run()이 초기 상태를 받아 워크플로우를 실행하는 패턴을 그대로 적용했다.

        clone_path는 job_id + CLONE_BASE_DIR로 항상 결정되므로
        DB에서 가져오지 않고 clone_node가 직접 계산한다.

        Args:
            job_id: 분석 작업 고유 ID
        """
        from app.core.database import async_session_factory
        from app.repo.pipeline.graph import AnalysisPipelineSupervisor
        from app.repo.pipeline.state import PipelineState

        try:
            # DB에서 job 메타데이터 조회 (repo_url, branch 등 필요)
            async with async_session_factory() as session:
                repo = AnalysisJobRepository(session)
                job = await repo.get_job_by_id(UUID(job_id))
                if not job:
                    logger.error(
                        f"파이프라인 실행 실패: job을 찾을 수 없음 (job_id={job_id})"
                    )
                    return

            # [Sec09 - initial_state] 워크플로우 초기 상태 구성
            # CustomerSupportSupervisor.run()에서 initial_state를 구성하는 패턴 참고
            initial_state: PipelineState = {
                "messages": [],
                "job_id": job_id,
                "repo_url": job.repo_url,
                "branch": job.branch,
                "owner": job.owner,
                "repo_name": job.repo_name,
                # clone_path는 None으로 시작한다.
                # clone_node가 os.path.exists()로 실제 파일 존재를 확인하여
                # 이미 Clone된 경우 단계를 건너끰다.
                "clone_path": None,
                "current_stage": PipelineStage.CLONE.value,
                "progress": 0,
                "status": JobStatus.IN_PROGRESS.value,
                "error": None,
            }

            # [Sec09 - work_flow.ainvoke()] LangGraph 워크플로우 실행
            supervisor = AnalysisPipelineSupervisor()
            await supervisor.run(initial_state)

        except Exception as exc:
            logger.exception("파이프라인 실행 실패 (job_id=%s)", job_id)

            # DB 상태 FAILED로 갱신
            async with async_session_factory() as session:
                repo = AnalysisJobRepository(session)
                await repo.update_job_status(
                    job_id=UUID(job_id),
                    status=JobStatus.FAILED.value,
                    message=f"파이프라인 실행 실패: {exc}",
                )
                await session.commit()

            # SSE/WebSocket 에러 이벤트 발행
            await self._publish_event(
                job_id=job_id,
                stage=PipelineStage.CLONE,
                status=JobStatus.FAILED,
                progress=0,
                message=f"파이프라인 실행 실패: {exc}",
            )

    # ──────────────────────────────────────────
    # 이벤트 발행 헬퍼
    # ──────────────────────────────────────────
    async def _publish_event(
        self,
        job_id: str,
        stage: PipelineStage,
        status: JobStatus,
        progress: int,
        message: str,
    ) -> None:
        """
        SSE/WebSocket 구독자에게 진행 상태 이벤트를 발행한다.

        Args:
            job_id: 분석 작업 고유 ID
            stage: 현재 파이프라인 단계
            status: 단계 상태
            progress: 전체 진행률 (0~100)
            message: 진행 상태 메시지
        """
        event = ProgressEvent(
            stage=stage,
            status=status,
            progress=progress,
            message=message,
            timestamp=datetime.now(timezone.utc),
        )
        await event_manager.publish(job_id, event)


# ──────────────────────────────────────────────
# API-002: GitHub URL 형식 및 접근 가능 여부 검증 서비스
# ──────────────────────────────────────────────
class RepoValidateService:
    """저장소 URL 검증 전용 서비스"""

    async def validate_repo(
        self,
        request: RepoValidateRequest,
    ) -> RepoValidateResponse:
        match = GITHUB_URL_PATTERN.match(request.repoUrl.strip())
        if not match:
            raise InvalidRepoUrlError(
                f"올바른 GitHub URL 형식이 아닙니다: {request.repoUrl}"
            )

        owner = match.group("owner")
        repo_name = match.group("repo")
        api_url = f"https://api.github.com/repos/{owner}/{repo_name}"

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    api_url,
                    headers={"User-Agent": "CodeMap"},
                )

            if response.status_code == 404:
                raise RepositoryNotFoundError(
                    "저장소가 없거나 접근할 수 없습니다."
                )
            if response.status_code >= 400:
                raise CodeMapException(
                    500,
                    "GITHUB_API_ERROR",
                    f"GitHub API 호출 중 오류가 발생했습니다: "
                    f"HTTP {response.status_code}",
                )

            payload = response.json()
        except RepositoryNotFoundError:
            raise
        except CodeMapException:
            raise
        except (httpx.RequestError, ValueError) as exc:
            raise CodeMapException(
                500,
                "GITHUB_API_ERROR",
                f"GitHub API 호출 중 오류가 발생했습니다: {exc}"
            ) from exc

        return RepoValidateResponse(
            code=200,
            message="success",
            data=RepoValidateData(
                valid=True,
                repoName=repo_name,
                owner=owner,
                defaultBranch=payload.get("default_branch", "main"),
                isPrivate=bool(payload.get("private", False)),
            ),
        )
