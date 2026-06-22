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
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from fastapi import BackgroundTasks, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import (
    AlreadyInProgressError,
    CloneFailedError,
    CloneNotCompletedError,
    CloneTimeoutError,
    CodeMapException,
    FileLimitExceededError,
    InvalidRepoUrlError,
    JobNotFoundError,
    PipelineAlreadyRunningError,
    PipelineStartFailedError,
    RepositoryNotFoundError,
)
from app.repo.event_manager import event_manager
from app.repo.models import AnalysisJob
from app.repo.local_upload import save_local_upload
from app.repo.repository import AnalysisJobRepository
from app.repo.schemas import (
    AnalysisData,
    AnalysisRequest,
    AnalysisResponse,
    CloneData,
    CloneRequest,
    CloneResponse,
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
    WorkspaceCleanupData,
    WorkspaceCleanupResponse,
)

logger = logging.getLogger(__name__)
settings = get_settings()

EXCLUDED_DIRS = {
    ".git",
    "node_modules",
    "build",
    "dist",
    "venv",
    ".venv",
    ".next",
    "__pycache__",
}
EXCLUDED_FILE_NAMES = {
    ".env",
    ".env.local",
    ".env.development",
    ".env.production",
    ".env.staging",
    "id_rsa",
    "id_dsa",
    "id_ecdsa",
    "id_ed25519",
    "id_rsa.pub",
    "id_dsa.pub",
    "id_ecdsa.pub",
    "id_ed25519.pub",
}
EXCLUDED_FILE_EXTENSIONS = {
    ".pem",
    ".key",
    ".p12",
    ".pfx",
    ".keystore",
    ".jks",
}
EXCLUDED_FILE_PREFIXES: tuple[str, ...] = ()

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

        # 2. 브랜치 미입력 시 git이 원격 기본 브랜치를 자동 선택한다.
        branch = request.branch or "default"

        # 3. 동일 저장소(레포)에 대한 중복 분석이 있는지 확인
        duplicate = await self.repository.check_duplicate_job(request.repoUrl, branch)
        if duplicate:
            return AnalysisResponse(
                code=201,
                message="success",
                data=AnalysisData(
                    jobId=duplicate.id,
                    repoName=duplicate.repo_name,
                    owner=duplicate.owner,
                    branch=duplicate.branch,
                    status=JobStatus(duplicate.status),
                    createdAt=duplicate.created_at,
                    model=duplicate.model_used,
                ),
            )

        # 4. DB에 새 분석 작업 생성
        job = await self.repository.create_job(
            repo_url=request.repoUrl,
            repo_name=repo_name,
            owner=owner,
            branch=branch,
            model_used=request.model,
            force_refresh=request.forceRefresh,
        )

        # 5. [Sec09 - supervisor.run()] 백그라운드에서 LangGraph 파이프라인 실행
        #    BackgroundTasks는 요청 의존성(get_db)의 commit보다 먼저 실행되므로,
        #    파이프라인의 독립 세션이 job을 조회할 수 있도록 여기서 먼저 commit한다.
        await self.db.commit()
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
                model=job.model_used,
            ),
        )

    async def register_local_analysis(
        self,
        folder_name: str,
        files: list[UploadFile],
        relative_paths: list[str],
        model: str,
        background_tasks: BackgroundTasks,
    ) -> AnalysisResponse:
        """Store a browser-selected directory and start the standard analysis pipeline."""
        repo_name = Path(folder_name).name.strip()[:255]
        if not repo_name or repo_name in {".", ".."}:
            raise CodeMapException(400, "INVALID_FOLDER_NAME", "올바른 폴더 이름이 필요합니다.")

        source_id = uuid4()
        job = await self.repository.create_job(
            repo_url=f"local-upload://{source_id}/{repo_name}",
            repo_name=repo_name,
            owner="local",
            branch="workspace",
            model_used=model or "auto",
            force_refresh=False,
        )
        workspace = Path(settings.CLONE_BASE_DIR) / str(job.id) / "repo"
        file_count, total_bytes = await save_local_upload(
            files,
            relative_paths,
            repo_name,
            workspace,
        )
        await self.repository.update_job_status(
            job_id=job.id,
            status=JobStatus.IN_PROGRESS.value,
            stage=PipelineStage.CLONE.value,
            progress=20,
            message=f"로컬 폴더 업로드 완료 · {file_count:,}개 파일 · {total_bytes / 1024 / 1024:.1f}MB",
        )
        # BackgroundTasks runs before the request dependency finalizer commits.
        # Make the uploaded job visible to the pipeline's independent DB session first.
        await self.db.commit()
        background_tasks.add_task(self._run_pipeline_with_langgraph, str(job.id))

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
                model=job.model_used,
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
                repoUrl=job.repo_url,
                stage=job.stage,
                progress=job.progress,
                statusMessage=job.message,
                model=job.model_used,
                report=job.report_json,
                createdAt=job.created_at,
                updatedAt=job.updated_at,
            ),
        )

    # ──────────────────────────────────────────
    # API-004: 특정 job 기준 저장소 clone 실행
    # ──────────────────────────────────────────
    async def clone_repository(
        self,
        job_id: UUID,
        request: CloneRequest,
    ) -> CloneResponse:
        """
        등록된 분석 작업의 저장소를 clone하고 불필요한 파일을 필터링한다.
        """
        job = await self.repository.get_job_by_id(job_id)
        if not job:
            raise JobNotFoundError()

        clone_path = Path(settings.CLONE_BASE_DIR) / str(job_id) / "repo"
        job_root = clone_path.parent

        if job.status == JobStatus.CLONED.value:
            raise CodeMapException(
                409,
                "CLONE_ALREADY_DONE",
                "이미 clone이 완료된 job입니다.",
            )

        # 이전 시도에서 남은 불완전 workspace 정리 후 재시도
        if clone_path.exists():
            await asyncio.to_thread(_safe_remove, job_root)

        await self.repository.update_job_status(
            job_id=job_id,
            status=JobStatus.IN_PROGRESS.value,
            stage=PipelineStage.CLONE.value,
            progress=5,
            message="저장소 clone을 시작합니다.",
        )

        try:
            await asyncio.to_thread(job_root.mkdir, parents=True, exist_ok=True)
            await self._run_git_clone(job.repo_url, job.branch, clone_path, request.timeoutSeconds)
            await asyncio.to_thread(_filter_workspace, clone_path)
            file_count, total_size = await asyncio.to_thread(_measure_workspace, clone_path)

            if (
                file_count > settings.MAX_FILE_COUNT
                or total_size > settings.MAX_REPO_SIZE_MB * 1024 * 1024
            ):
                await asyncio.to_thread(_safe_remove, job_root)
                await self.repository.update_job_status(
                    job_id=job_id,
                    status=JobStatus.FAILED.value,
                    stage=PipelineStage.CLONE.value,
                    progress=0,
                    message="분석 가능한 파일 수 또는 용량 제한을 초과했습니다.",
                )
                await self.db.commit()
                raise FileLimitExceededError()

            await self.repository.update_job_status(
                job_id=job_id,
                status=JobStatus.CLONED.value,
                stage=PipelineStage.CLONE.value,
                progress=20,
                message="저장소 clone이 완료되었습니다.",
            )
            await self.db.commit()

            return CloneResponse(
                code=200,
                message="success",
                data=CloneData(
                    jobId=job_id,
                    clonePath=f"jobs/{job_id}",
                    fileCount=file_count,
                    sizeKb=(total_size + 1023) // 1024,
                ),
            )
        except CodeMapException:
            raise
        except asyncio.TimeoutError as exc:
            await asyncio.to_thread(_safe_remove, job_root)
            await self.repository.update_job_status(
                job_id=job_id,
                status=JobStatus.FAILED.value,
                stage=PipelineStage.CLONE.value,
                progress=0,
                message="clone 제한 시간이 초과되었습니다.",
            )
            await self.db.commit()
            raise CloneTimeoutError() from exc
        except Exception as exc:
            logger.exception("clone_repository failed (job_id=%s)", job_id)
            await asyncio.to_thread(_safe_remove, job_root)
            await self.repository.update_job_status(
                job_id=job_id,
                status=JobStatus.FAILED.value,
                stage=PipelineStage.CLONE.value,
                progress=0,
                message="저장소 clone 중 오류가 발생했습니다.",
            )
            await self.db.commit()
            raise CloneFailedError(str(exc) or "저장소 clone 중 오류가 발생했습니다.") from exc

    async def _run_git_clone(
        self,
        repo_url: str,
        branch: str,
        clone_path: Path,
        timeout_seconds: int,
    ) -> None:
        import subprocess

        def _do_clone() -> subprocess.CompletedProcess:
            proc = subprocess.Popen(
                ["git", "clone", "--depth", "1", "--branch", branch, repo_url, str(clone_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                stdout, stderr = proc.communicate(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
                # timeout 시 partial workspace 즉시 정리
                _safe_remove(clone_path)
                raise
            return subprocess.CompletedProcess(proc.args, proc.returncode, stdout, stderr)

        try:
            result = await asyncio.to_thread(_do_clone)
        except subprocess.TimeoutExpired as exc:
            raise asyncio.TimeoutError() from exc

        if result.returncode != 0:
            # clone 실패 시 partial workspace 정리
            _safe_remove(clone_path)
            error_message = result.stderr.strip() or result.stdout.strip()
            logger.error(
                "git clone failed: returncode=%d stderr=%r stdout=%r",
                result.returncode,
                result.stderr.strip(),
                result.stdout.strip(),
            )
            raise RuntimeError(error_message or f"git exited with code {result.returncode}")

        # clone 완료 marker 생성 (atomic completion 표시)
        (clone_path / ".clone_complete").write_text("ok", encoding="utf-8")

    # ──────────────────────────────────────────
    # API-008: 임시 clone 디렉토리 cleanup
    # ──────────────────────────────────────────
    async def cleanup_workspace(self, job_id: UUID) -> WorkspaceCleanupResponse:
        """
        분석 작업의 임시 clone 디렉토리를 삭제한다.
        
        """
        job = await self.repository.get_job_by_id(job_id)
        if not job:
            raise JobNotFoundError()

        if job.status == JobStatus.IN_PROGRESS.value:
            raise CodeMapException(
                409,
                "WORKSPACE_IN_USE",
                "분석 파이프라인이 진행 중인 workspace는 삭제할 수 없습니다.",
            )

        clone_path = Path(settings.CLONE_BASE_DIR) / str(job_id) / "repo"
        if not clone_path.exists():
            raise CodeMapException(
                404,
                "WORKSPACE_NOT_FOUND",
                "임시 clone 디렉토리가 존재하지 않습니다.",
            )

        try:
            await asyncio.to_thread(_safe_remove, clone_path)
            await asyncio.to_thread(_remove_empty_parent, clone_path.parent)
        except OSError as exc:
            logger.exception("workspace cleanup failed (job_id=%s)", job_id)
            raise CodeMapException(
                500,
                "WORKSPACE_CLEANUP_FAILED",
                "임시 작업 디렉토리 정리에 실패했습니다.",
            ) from exc

        return WorkspaceCleanupResponse(
            code=200,
            message="success",
            data=WorkspaceCleanupData(
                jobId=job_id,
                cleanedPath=str(clone_path),
                cleanedAt=datetime.now(timezone.utc),
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
        clone_complete_marker = os.path.join(clone_path, ".clone_complete")
        if not os.path.exists(clone_path) or not os.path.exists(clone_complete_marker):
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
                "model": job.model_used,
                "force_refresh": job.force_refresh,
                "analysis_report": job.report_json,
                # clone_path는 None으로 시작한다.
                # clone_node가 os.path.exists()로 실제 파일 존재를 확인하여
                # 이미 Clone된 경우 단계를 건너끰다.
                "clone_path": None,
                "current_stage": PipelineStage.CLONE.value,
                "progress": 0,
                "status": JobStatus.IN_PROGRESS.value,
                "error": None,
                "timings": {},  # 파이프라인 단계별 소요 시간 (초) — 완료 시 [TIMING SUMMARY] 로그에 출력
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


def _filter_workspace(repo_dir: Path) -> None:
    for dirpath_str, dirnames, filenames in os.walk(str(repo_dir), topdown=True, followlinks=False):
        dirpath = Path(dirpath_str)

        # excluded 디렉토리 제거 및 하위 순회 차단 (dirnames in-place 수정)
        excluded = [d for d in dirnames if d in EXCLUDED_DIRS]
        for d in excluded:
            _safe_remove(dirpath / d)
            dirnames.remove(d)

        # 심볼릭 링크 디렉토리 제거 (followlinks=False이므로 순회 안 됨, 직접 삭제 필요)
        symlinked = [d for d in dirnames if (dirpath / d).is_symlink()]
        for d in symlinked:
            (dirpath / d).unlink(missing_ok=True)
            dirnames.remove(d)

        # 파일 처리: 심볼릭 링크 및 제외 대상 삭제
        for fname in filenames:
            fpath = dirpath / fname
            if fpath.is_symlink() or _should_remove_file(fpath):
                fpath.unlink(missing_ok=True)


def _should_remove_file(path: Path) -> bool:
    lower_name = path.name.lower()
    if lower_name in EXCLUDED_FILE_NAMES:
        return True
    if EXCLUDED_FILE_PREFIXES and lower_name.startswith(EXCLUDED_FILE_PREFIXES):
        return True
    if path.suffix.lower() in EXCLUDED_FILE_EXTENSIONS:
        return True
    return _is_binary_file(path)


def _is_binary_file(path: Path) -> bool:
    if path.is_symlink():
        return True
    try:
        with path.open("rb") as f:
            chunk = f.read(1024)
    except OSError:
        return True
    # UTF-16 BOM(LE: FF FE, BE: FE FF)이면 텍스트로 판단
    if chunk[:2] in (b'\xff\xfe', b'\xfe\xff'):
        return False
    return b"\0" in chunk


def _measure_workspace(repo_dir: Path) -> tuple[int, int]:
    file_count = 0
    total_size = 0
    for path in repo_dir.rglob("*"):
        if path.is_file() and not path.is_symlink():
            file_count += 1
            total_size += path.stat().st_size
    return file_count, total_size


def _safe_remove(path: Path) -> None:
    if path.exists():
        import os, stat, sys

        def _on_error(func, fpath, _exc_info):
            os.chmod(fpath, stat.S_IWRITE)
            func(fpath)

        def _on_exc(func, fpath, _exc):
            os.chmod(fpath, stat.S_IWRITE)
            func(fpath)

        if sys.version_info >= (3, 12):
            shutil.rmtree(path, onexc=_on_exc)
        else:
            shutil.rmtree(path, onerror=_on_error)


def _remove_empty_parent(path: Path) -> None:
    try:
        path.rmdir()
    except OSError:
        return
