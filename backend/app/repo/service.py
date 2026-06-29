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

from app.infra.config import get_settings
from app.common import access
from app.common.exceptions import (
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
from app.pipeline.event_manager import event_manager
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
    async def register_analysis(self, request: AnalysisRequest, background_tasks: BackgroundTasks, user_id: UUID | None = None) -> AnalysisResponse:
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
        ## visibility/teamId 정합성을 명시적으로 검증한다. (자체 PR 리뷰 M2)
        ##  - visibility는 단일 진실원(source of truth). legacy isPrivate는 더 이상 사용하지 않는다.
        ##  - teamId가 있는데 visibility!=team이면 조용히 private 저장되는 일이 없도록 거부한다.
        visibility = (request.visibility or "private").lower()
        if visibility not in {"private", "team"}:
            raise CodeMapException(400, "INVALID_VISIBILITY", "visibility는 private 또는 team이어야 합니다.")
        if request.teamId is not None and visibility != "team":
            raise CodeMapException(400, "INVALID_VISIBILITY", "teamId가 지정되면 visibility는 team이어야 합니다.")
        team_id, is_private = await self._resolve_visibility(visibility, request.teamId, user_id)

        # 3. 동일 저장소(레포)에 대한 중복 분석이 있는지 확인
        duplicate = await self.repository.check_duplicate_job(
            request.repoUrl,
            branch,
            user_id=user_id,
            team_id=team_id,
        )
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
            user_id=user_id,
            is_private=is_private,
            team_id=team_id,
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
        user_id: UUID | None = None,
        visibility: str = "private",
        team_id: UUID | None = None,
    ) -> AnalysisResponse:
        """Store a browser-selected directory and start the standard analysis pipeline."""
        repo_name = Path(folder_name).name.strip()[:255]
        if not repo_name or repo_name in {".", ".."}:
            raise CodeMapException(400, "INVALID_FOLDER_NAME", "올바른 폴더 이름이 필요합니다.")

        source_id = uuid4()
        visibility = (visibility or "private").lower()
        if visibility not in {"private", "team"}:
            raise CodeMapException(400, "INVALID_VISIBILITY", "visibility는 private 또는 team이어야 합니다.")
        if team_id is not None and visibility != "team":
            raise CodeMapException(400, "INVALID_VISIBILITY", "teamId가 지정되면 visibility는 team이어야 합니다.")
        team_id, is_private = await self._resolve_visibility(visibility, team_id, user_id)
        job = await self.repository.create_job(
            repo_url=f"local-upload://{source_id}/{repo_name}",
            repo_name=repo_name,
            owner="local",
            branch="workspace",
            model_used=model or "auto",
            force_refresh=False,
            user_id=user_id,
            is_private=is_private,
            team_id=team_id,
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
    async def get_job_status(self, job_id: UUID, current_user_id: UUID | None = None) -> JobStatusResponse:
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
        if not await self.can_access_job(job, current_user_id):
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
                report=_format_report_for_frontend(job.report_json, job.repo_name),
                createdAt=job.created_at,
                updatedAt=job.updated_at,
            ),
        )

    async def _resolve_visibility(
        self,
        visibility: str,
        team_id: UUID | None,
        user_id: UUID | None,
    ) -> tuple[UUID | None, bool]:
        """visibility 입력을 (team_id, is_private)로 환산하고 권한을 검증한다."""
        if visibility == "team":
            if user_id is None:
                raise CodeMapException(400, "TEAM_REQUIRES_AUTH", "팀 공유 분석은 로그인 후 사용할 수 있습니다.")
            if team_id is None:
                raise CodeMapException(400, "TEAM_ID_REQUIRED", "팀 공유 분석에는 teamId가 필요합니다.")
            if not await self.repository.user_has_team_access(team_id, user_id):
                raise CodeMapException(403, "TEAM_ACCESS_DENIED", "해당 팀에 접근할 수 없습니다.")
            return team_id, False
        ## private: 로그인 필수 (비로그인 공개 분석 생성은 더 이상 허용하지 않는다. 자체 PR 리뷰 M1)
        if user_id is None:
            raise CodeMapException(400, "PRIVATE_REQUIRES_AUTH", "개인 분석은 로그인 후 사용할 수 있습니다.")
        return None, True

    async def can_access_job(self, job, current_user_id: UUID | None) -> bool:
        ## 단일 판정 모듈에 위임 (자체 PR 리뷰 M3)
        return await access.can_access_job(self.db, job, current_user_id)

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
        # get_db() finalizer의 자동 commit이 PR #96에서 제거됐으므로 명시적으로 commit.
        # BackgroundTask가 실행되기 전 IN_PROGRESS 상태가 DB에 반드시 저장돼야
        # 독립 세션으로 동작하는 파이프라인이 올바른 상태를 조회할 수 있다.
        await self.db.commit()

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
        from app.infra.database import async_session_factory
        from app.pipeline.graph import AnalysisPipelineSupervisor
        from app.pipeline.state import PipelineState

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
            final_state = await supervisor.run(initial_state)

            # 노드 내부에서 예외를 삼키고 FAILED 상태를 반환한 경우
            # (doc_gen / onboarding 등) _update_db·_publish는 이미 해당 노드에서 완료되므로
            # 후속 RAG 파싱을 건너뛰고 조기 종료한다.
            if final_state and final_state.get("status") == JobStatus.FAILED.value:
                logger.warning(
                    "파이프라인 FAILED 상태로 종료 — RAG 인덱싱 건너술 (job=%s stage=%s error=%s)",
                    job_id,
                    final_state.get("current_stage"),
                    final_state.get("error"),
                )
                return

            # 분석(그래프) 완료 후, 같은 백그라운드에서 RAG 정밀 파싱(청킹·코드맵)을
            # report_json에 병합하고 청크를 임베딩해 pgvector에 적재한다.
            # 분석은 이미 COMPLETED로 보고되어 사용자 응답을 막지 않으며,
            # 이 단계의 실패는 _run_parse_and_embed 내부에서 흡수한다(분석 결과 영향 없음).
            await self._run_parse_and_embed(job_id)

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
    # RAG 인덱싱: 분석 완료 후 정밀 파싱 + 임베딩 (백그라운드 연속 실행)
    # ──────────────────────────────────────────
    async def _run_parse_and_embed(self, job_id: str) -> None:
        """분석(LangGraph) 완료 후 RAG 정밀 파싱·임베딩을 이어서 실행한다.

        - run_parse_pipeline: 청킹·계층 요약·코드맵 등 canonical 산출물을 만들어
          report_json에 병합한다(상세 조회 API가 실데이터를 받도록, 기존 키는 보존).
        - run_embed_pipeline: 청크를 임베딩해 pgvector에 적재한다(OPENAI_API_KEY 있을 때만).

        분석 완료(COMPLETED)는 이미 보고되었으므로 사용자 응답을 막지 않으며,
        이 단계의 실패는 분석 결과에 영향을 주지 않도록 내부에서 흡수한다.
        세션/commit은 기존 백그라운드 패턴과 동일하게 독립 세션으로 처리한다.
        """
        from app.infra.database import async_session_factory
        from app.embed.service import embed_ready, run_embed_pipeline
        from app.parse import service as parse_service
        from app.parse.schemas import EmbedRequest

        settings = get_settings()
        clone_path = os.path.join(settings.CLONE_BASE_DIR, job_id, "repo")

        async def _write_rag_index_status(status: str, chunks: int = 0) -> None:
            """early return / 예외 경로에서 rag_index 상태를 DB에 안전하게 기록한다."""
            try:
                async with async_session_factory() as session:
                    _repo = AnalysisJobRepository(session)
                    _job = await _repo.get_job_by_id(UUID(job_id))
                    if _job:
                        _report = dict(_job.report_json or {})
                        _report["rag_index"] = {"status": status, "chunks": chunks}
                        await _repo.update_job_status(
                            job_id=UUID(job_id),
                            status=_job.status,
                            report_json=_report,
                        )
                        await session.commit()
            except Exception as _exc:
                logger.error("[RAG 인덱싱] rag_index 상태 기록 실패 job=%s: %s", job_id, _exc)

        try:
            await _write_rag_index_status("in_progress")

            # 1. 분석 메타 조회 — 성공(COMPLETED) 건만 인덱싱한다.
            async with async_session_factory() as session:
                repo = AnalysisJobRepository(session)
                job = await repo.get_job_by_id(UUID(job_id))
                if not job:
                    # job 자체가 없으면 기록할 대상 없음 — 그냥 반환
                    return
                if job.status != JobStatus.COMPLETED.value:
                    logger.info(
                        "[RAG 인덱싱] 분석 미완료(status=%s), 건너뜀 (job=%s)",
                        job.status, job_id,
                    )
                    # 분석 자체가 실패/취소된 경우 → skipped 기록 후 반환
                    await _write_rag_index_status("skipped")
                    return
                owner, repo_name, branch = job.owner, job.repo_name, job.branch
                force_refresh = bool(job.force_refresh)
                report = dict(job.report_json or {})
                current_status = job.status

            if not os.path.isdir(clone_path):
                logger.warning("[RAG 인덱싱] clone 경로 없음, 건너뜀 (job=%s)", job_id)
                # clone이 없으면 임베딩 불가 → skipped 기록 후 반환 (무한 폴링 방지)
                await _write_rag_index_status("skipped")
                return

            # 2. 정밀 파싱 → report_json에 canonical 결과 병합 (additive: 기존 키 보존)
            result = await parse_service.run_parse_pipeline(
                job_id=UUID(job_id),
                repo_name=repo_name,
                owner=owner,
                branch=branch,
                clone_path=clone_path,
            )
            parse_data = result.model_dump(mode="json")
            for key in (
                "tech_stack_details", "language_composition", "entry_point_details",
                "run_command_details", "config_files", "master_summary",
                "folder_summaries", "file_summaries", "file_map", "heatmap",
                "directory_tree", "files",
            ):
                report[key] = parse_data[key]

            # 3. 임베딩 → pgvector (API 키 있을 때만; 없으면 파스 결과만 반영)
            index_status, saved_chunks = "skipped", 0
            if settings.OPENAI_API_KEY.get_secret_value():
                async with async_session_factory() as session:
                    embed_result = await run_embed_pipeline(
                        session,
                        EmbedRequest(
                            job_id=UUID(job_id),
                            files=result.files,
                            force_reembed=force_refresh,
                        ),
                    )
                saved_chunks = embed_result.saved_chunks
                # saved_chunks는 upsert된 CHUNK row 수일 뿐, 임베딩 배치 실패 시
                # embedding=None인 row도 포함된다. 실제 non-null 임베딩 존재 여부로
                # status를 정해 embed_ready()(벡터 검색 가능 여부)와 항상 일치시킨다.
                async with async_session_factory() as session:
                    has_vectors = await embed_ready(session, UUID(job_id))
                index_status = "ready" if has_vectors else "empty"
            report["rag_index"] = {"status": index_status, "chunks": saved_chunks}

            # 4. report_json 갱신 저장 (분석 status는 그대로 보존)
            async with async_session_factory() as session:
                repo = AnalysisJobRepository(session)
                await repo.update_job_status(
                    job_id=UUID(job_id),
                    status=current_status,
                    report_json=report,
                )
                await session.commit()

            logger.info(
                "[RAG 인덱싱] 완료 job=%s | status=%s 청크=%d",
                job_id, index_status, saved_chunks,
            )
        except Exception as exc:
            # RAG 인덱싱 실패는 분석 결과에 영향을 주지 않는다(분석은 이미 완료).
            logger.exception("[RAG 인덱싱] 실패 (분석 결과 영향 없음) job=%s: %s", job_id, exc)
            # 실패 시 report_json에 rag_index.status = "failed" 명시 (무한 대기 방지)
            await _write_rag_index_status("failed")

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

    # ──────────────────────────────────────────
    # execute_analysis_and_persist
    # ──────────────────────────────────────────
    async def execute_analysis_and_persist(
        self, job_id: UUID, clone_path: str, repo_name: str
    ) -> dict:
        """
        CWD 경로 기반으로 개별 정적 분석 도구들을 병렬로 호출하여
        최종 report_json 딕셔너리를 조립하고 DB에 입력합니다.
        """
        from uuid import UUID
        from app.repo.schemas import JobStatus, PipelineStage
        from app.tool.dir_scan import list_repository_files
        from app.tool.file_read import extract_file_static_metadata
        from app.tool.grep_scan import count_todo_annotations
        from app.tool.env_validation import verify_build_environment
        from app.tool.ast_quality import (
            calculate_code_complexity,
        )

        root = Path(clone_path).resolve()

        ## 1. 파일 리스트 추출 (디렉토리 스캔 전담)
        file_paths = await asyncio.to_thread(list_repository_files, root)
        total_files = len(file_paths)

        if total_files == 0:
            ## 예외 폴백: 소스 파일이 없는 경우
            report = {
                "repository": {"name": repo_name, "root": str(root)},
                "stats": {
                    "files": 0, "lines": 0, "bytes": 0, "todos": 0,
                    "tests": 0, "primary_language": "Unknown",
                },
                "languages": [],
                "stack": [],
                "entrypoints": [],
                "files": [],
                "health_score": 50,
                "health_metrics": {
                    "score": 50,
                    "test_ratio": 0.0,
                    "todo_ratio": 0.0,
                    "oversized_ratio": 0.0,
                    "duplicate_code_ratio": 0.0,
                },
                "executive_summary": "분석 대상 텍스트 파일이 없는 빈 저장소입니다.",
                "key_strengths": ["분석 대상 텍스트 파일이 없습니다."],
                "key_risks": [
                    "레포지토리가 비어 있거나 소스코드가 감지되지 않습니다."
                ],
                "recommendations": [],
            }
            await self.repository.update_job_status(
                job_id=job_id,
                status=JobStatus.IN_PROGRESS.value,
                stage=PipelineStage.CODE_MAP.value,
                progress=55,
                message="분석 대상 텍스트 파일이 없습니다.",
                report_json=report,
            )
            await self.db.commit()
            return report

        ## 2. 기본 파일 물리 정보 일괄 스캔 (I/O 병렬 구동)
        file_meta = await asyncio.to_thread(
            extract_file_static_metadata, file_paths, root
        )

        ## 주 언어 판별 및 언어 통계 산정
        from collections import Counter
        languages = Counter()
        total_lines = 0
        total_bytes = 0
        test_files = 0

        oversized: list[str] = []
        code_line_files: dict[str, set[str]] = {}
        significant_code_lines = 0

        from app.repo.analyzer import CODE_SUFFIXES, _read_text, _normalized_code_lines
        for f in file_meta:
            total_lines += f["lines"]
            total_bytes += f["bytes"]
            languages[f["language"]] += f["lines"]
            
            path_str = f["path"]
            name_str = f["name"]
            
            if "test" in name_str.lower() or "test" in path_str.lower():
                test_files += 1

            # main의 중복도 검출 및 대형 파일 수집 적용
            full_path = root / path_str
            suffix = full_path.suffix.lower()
            if suffix in CODE_SUFFIXES:
                text = _read_text(full_path, limit=100_000)
                normalized_lines = _normalized_code_lines(text)
                significant_code_lines += len(normalized_lines)
                for normalized_line in set(normalized_lines):
                    code_line_files.setdefault(normalized_line, set()).add(path_str)
                
                if f["lines"] > 700:
                    oversized.append(path_str)

        primary_language = (
            languages.most_common(1)[0][0] if languages else "Unknown"
        )
        test_ratio = test_files / max(total_files, 1)

        ## 3. 남은 분석 도구 병렬 호출 (asyncio.gather)
        todo_task = asyncio.to_thread(count_todo_annotations, file_paths)
        env_task = asyncio.to_thread(
            verify_build_environment, file_paths, primary_language, root
        )
        ast_task = asyncio.to_thread(calculate_code_complexity, file_paths)

        todo_res, env_res, ast_res = await asyncio.gather(
            todo_task, env_task, ast_task
        )

        # main의 지표 산정 모델 전면 이식
        todo_ratio = todo_res["total_todos"] / max(1, total_files)
        oversized_ratio = len(oversized) / max(1, total_files)
        duplicate_code_lines = sum(
            len(paths) - 1
            for paths in code_line_files.values()
            if len(paths) > 1
        )
        duplicate_code_ratio = duplicate_code_lines / max(significant_code_lines, 1)
        duplicate_files = sorted({
            path
            for paths in code_line_files.values()
            if len(paths) > 1
            for path in paths
        })

        score = 100
        score -= min(30, int(oversized_ratio * 100))
        score -= min(20, int(todo_ratio * 50))
        score -= min(25, int(duplicate_code_ratio * 100))

        health_score = max(35, min(100, score))
        health_metrics = {
            "score": health_score,
            "test_ratio": round(test_ratio, 3),
            "todo_ratio": round(todo_ratio, 3),
            "oversized_ratio": round(oversized_ratio, 3),
            "duplicate_code_ratio": round(duplicate_code_ratio, 3),
        }

        report = {
            "repository": {"name": repo_name, "root": str(root)},
            "stats": {
                "files": total_files,
                "lines": total_lines,
                "bytes": total_bytes,
                "todos": todo_res["total_todos"],
                "tests": test_files,
                "primary_language": primary_language,
            },
            "languages": [
                {"name": name, "lines": lines}
                for name, lines in languages.most_common(8)
            ],
            "stack": env_res["detected_stack"],
            "entrypoints": env_res["entrypoints"][:12],
            "files": file_meta,
            "health_score": health_score,
            "health_metrics": health_metrics,
            "executive_summary": (
                f"{repo_name}은(는) {primary_language} 중심의 코드베이스입니다. "
                "실제 파일 구조, 진입점, 구성 파일과 유지보수 신호를 기준으로 분석했습니다."
            ),
            "key_strengths": [
                f"{total_files:,}개 파일과 {total_lines:,}줄이 "
                "실제 스냅샷에서 확인되었습니다.",
            ],
            "key_risks": [],
            "recommendations": [],
        }

        ## 분석 소견/가이드라인 보강
        if not env_res["has_mandatory_manifest"]:
            report["key_risks"].append(
                f"{primary_language} 빌드 구성 파일이 결락되어 "
                "실행이 불가할 수 있습니다."
            )
            report["recommendations"].append({
                "title": "빌드 설정 파일 추가",
                "detail": "의존성 패키지 관리 파일을 루트 디렉토리에 추가하세요.",
                "affected_files": [],
                "priority": "high",
            })

        ## 7. DB 최종 영속화 및 커밋
        await self.repository.update_job_status(
            job_id=job_id,
            status=JobStatus.IN_PROGRESS.value,
            stage=PipelineStage.CODE_MAP.value,
            progress=55,
            message=f"{total_files}개 파일 구조 분석 완료",
            report_json=report,
        )
        await self.db.commit()
        return report


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

        headers = {"User-Agent": "CodeMap"}
        if settings.GITHUB_TOKEN:
            headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(
                    api_url,
                    headers=headers,
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


# ──────────────────────────────────────────────
# _format_report_for_frontend
# ──────────────────────────────────────────────
def _format_report_for_frontend(
    report: dict | None, repo_name: str
) -> dict | None:
    """
    DB에 적재된 순수 분석 데이터(report_json)를 프론트엔드가 기대하는 DTO 규격
    (size, kind, executive_summary 등 필수 필드)으로 실시간 맵핑하여 반환한다.
    """
    if not report:
        return None

    formatted = dict(report)

    # 1. executive_summary 누락 시 기본 폴백 합성
    if "executive_summary" not in formatted:
        stats = formatted.get("stats", {})
        primary_lang = stats.get("primary_language", "Unknown")
        total_files = stats.get("files", 0)

        if total_files == 0:
            formatted["executive_summary"] = (
                f"{repo_name}은(는) 분석 가능한 텍스트 파일이 감지되지 않은 "
                "저장소입니다. 파일 구조와 실행 신호가 부족해 제한된 리포트를 "
                "생성했습니다."
            )
        else:
            formatted["executive_summary"] = (
                f"{repo_name}은(는) {primary_lang} 중심의 코드베이스입니다. "
                "실제 파일 구조, 진입점, 구성 파일과 유지보수 신호를 기준으로 분석했습니다."
            )

    # 2. files 리스트 내 size, kind 누락 시 매핑 보강
    if "files" in formatted and isinstance(formatted["files"], list):
        mapped_files = []
        for f in formatted["files"]:
            if not isinstance(f, dict):
                mapped_files.append(f)
                continue

            file_item = dict(f)
            if "kind" not in file_item:
                name = file_item.get("name", "")
                path = file_item.get("path", "")
                file_item["kind"] = (
                    "test"
                    if ("test" in name.lower() or "test" in path.lower())
                    else "source"
                )
            mapped_files.append(file_item)
        formatted["files"] = mapped_files

    return formatted
