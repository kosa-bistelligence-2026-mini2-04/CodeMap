"""
분석 작업 REST API 라우터 (Controller/진입점)

API 명세서에 정의된 HTTP 엔드포인트를 FastAPI 라우터로 구현한다.
각 엔드포인트는 Service 계층에 비즈니스 로직을 위임한다.

담당 API:
  - API-001: POST /api/repo/analysis (프로젝트 등록)
  - API-003: GET  /api/repo/analysis/{job_id} (상태 조회)
  - API-005: GET  /api/repo/analysis/{job_id}/events (SSE 스트림)
  - API-007: POST /api/repo/analysis/{job_id}/start (파이프라인 시작)
  - API-FILE: GET  /api/repo/analysis/{job_id}/files/content (파일 컨텐츠 조회)
"""

import json
import logging
from pathlib import Path
from uuid import UUID
from typing import Annotated

import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.auth import get_current_user_optional
from app.infra.database import async_session_factory, get_db
from app.common.exceptions import (
    BinaryFileError,
    FilePathForbiddenError,
    JobAlreadyDoneError,
    JobNotFoundError,
    WorkspaceNotReadyError,
    build_error_response,
)
from app.pipeline.event_manager import event_manager
from app.repo.schemas import (
    AnalysisRequest,
    AnalysisResponse,
    CloneRequest,
    CloneResponse,
    ErrorResponse,
    FileContentData,
    FileContentResponse,
    JobStatus,
    JobStatusResponse,
    PipelineStartResponse,
    RepoValidateRequest,
    RepoValidateResponse,
    WorkspaceCleanupResponse,
)
from app.repo.service import AnalysisService, RepoValidateService
from app.embed.repository import EmbedRepository
from app.infra.config import get_settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# APIRouter 인스턴스 생성
# ──────────────────────────────────────────────
router = APIRouter(tags=["Project Repository Analysis"])


@router.get("/api/repo/models", summary="분석 모델 정책 조회")
async def list_models():
    settings = get_settings()
    return {
        "provider": "openai" if settings.OPENAI_API_KEY else "custom",
        "base_url": None,
        "default_model": "auto",
        "models": [
            {
                "id": "auto",
                "label": "자동 선택",
                "hint": "저장소 구조 분석은 항상 실제 파일 스캔으로 수행하고, 서버 모델 설정이 있으면 설명을 보강합니다.",
            },
            {
                "id": settings.OPENAI_MODEL,
                "label": settings.OPENAI_MODEL,
                "hint": "서버에 설정된 생성형 모델을 분석 설명에 사용합니다.",
            },
        ] if settings.OPENAI_API_KEY else [{
            "id": "auto",
            "label": "자동 선택",
            "hint": "현재 서버는 결정론적 구조 분석 모드입니다.",
        }],
    }


@router.get("/api/repo/analyses", summary="최근 분석 프로젝트 조회")
async def list_analyses(limit: int = 30, db: AsyncSession = Depends(get_db)):
    jobs = await AnalysisService(db).repository.list_jobs(limit)
    status_map = {"IN_PROGRESS": "running", "COMPLETED": "completed", "FAILED": "failed"}
    return {"items": [{
        "job_id": str(job.id),
        "source": "local" if job.repo_url.startswith("local-upload://") else "github",
        "path": job.repo_url,
        "status": status_map.get(job.status, "failed"),
        "created_at": job.created_at.timestamp(),
        "completed_at": job.updated_at.timestamp() if job.status == "COMPLETED" else None,
        "total_pipeline_ms": None,
        "error_message": job.message if job.status == "FAILED" else None,
        "model_used": job.model_used,
        "force_refresh": job.force_refresh,
    } for job in jobs]}


# ──────────────────────────────────────────────
# API-002: GitHub URL 형식 및 접근 가능 여부 검증
# POST /api/repo/validate
# ──────────────────────────────────────────────
@router.post(
    "/api/repo/validate",
    response_model=RepoValidateResponse,
    summary="GitHub URL 형식 및 접근 가능 여부 검증",
    description="입력된 GitHub 저장소 URL의 형식과 실제 접근 가능 여부를 확인한다.",
    responses={
        400: {"model": ErrorResponse, "description": "GitHub URL 형식 오류"},
        404: {"model": ErrorResponse, "description": "저장소 없음 또는 접근 불가"},
        500: {"model": ErrorResponse, "description": "GitHub API 호출 오류"},
    },
)
async def validate_repo(request: RepoValidateRequest) -> RepoValidateResponse:
    """Clone 이전 단계에서 저장소 URL을 검증한다."""
    service = RepoValidateService()
    return await service.validate_repo(request)


# ──────────────────────────────────────────────
# API-001: 프로젝트 등록 (분석 요청)
# POST /api/repo/analysis
# ──────────────────────────────────────────────
from app.infra.auth import get_current_user_optional, verify_access_token
from app.common.exceptions import UnauthorizedError


def _user_id_from_token(token: str | None) -> UUID | None:
    """SSE(EventSource)는 헤더를 보낼 수 없으므로 query param 토큰을 검증한다."""
    if not token:
        return None
    try:
        payload = verify_access_token(token)
        return UUID(str(payload["sub"]))
    except (UnauthorizedError, KeyError, ValueError, TypeError):
        return None

@router.post(
    "/api/repo/analysis",
    response_model=AnalysisResponse,
    status_code=201,
    summary="프로젝트 등록 (분석 요청)",
    description="GitHub 저장소 URL을 받아 분석 작업을 등록하고 job_id를 발급한다.",
    responses={
        400: {"model": ErrorResponse, "description": "GitHub URL 형식 오류"},
        404: {"model": ErrorResponse, "description": "저장소 없음 또는 접근 불가"},
        408: {"model": ErrorResponse, "description": "Clone 제한 시간 초과"},
        409: {"model": ErrorResponse, "description": "동일 저장소 분석 진행 중"},
        413: {"model": ErrorResponse, "description": "파일 수/용량 제한 초과"},
        422: {"model": ErrorResponse, "description": "저장소 용량 초과 (GitHub API 기준)"},
    },
)
async def register_analysis(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: Annotated[dict | None, Depends(get_current_user_optional)],
    db: AsyncSession = Depends(get_db),
) -> AnalysisResponse:
    """
    GitHub 저장소 URL을 받아 분석 작업을 등록한다.

    내부적으로 URL 검증 → Clone → Code Map → Doc Generation →
    Onboarding Guide → Report 저장 순서로 비동기 처리되며,
    각 단계의 진행 상태는 WebSocket으로 실시간 push된다.
    """
    ## 분석 기록은 항상 소유자/팀에 귀속되므로 로그인 필수. (자체 PR 리뷰 M1)
    ##  visibility/teamId 정합성 및 팀 권한 검증은 service._resolve_visibility가 담당한다.
    if current_user is None:
        raise HTTPException(
            status_code=400,
            detail=build_error_response(
                status_code=400,
                message="분석 기록 저장은 로그인 후 사용할 수 있습니다.",
                error_code="PRIVATE_REQUIRES_AUTH",
                field="visibility",
            ),
        )
    service = AnalysisService(db)
    user_id = UUID(current_user["sub"]) if current_user and "sub" in current_user else None
    return await service.register_analysis(request, background_tasks, user_id=user_id)


@router.post(
    "/api/repo/analysis/local",
    response_model=AnalysisResponse,
    status_code=201,
    summary="로컬 폴더 업로드 및 분석 요청",
)
async def register_local_analysis(
    background_tasks: BackgroundTasks,
    folder_name: str = Form(..., alias="folderName"),
    relative_paths: list[str] = Form(..., alias="paths"),
    files: list[UploadFile] = File(...),
    model: str = Form("auto"),
    visibility: str = Form("private"),
    team_id: UUID | None = Form(None, alias="teamId"),
    current_user: Annotated[dict | None, Depends(get_current_user_optional)] = None,
    db: AsyncSession = Depends(get_db),
) -> AnalysisResponse:
    """Upload a browser-selected directory into an isolated analysis workspace."""
    user_id = UUID(current_user["sub"]) if current_user and "sub" in current_user else None
    return await AnalysisService(db).register_local_analysis(
        folder_name=folder_name,
        files=files,
        relative_paths=relative_paths,
        model=model,
        background_tasks=background_tasks,
        user_id=user_id,
        visibility=visibility,
        team_id=team_id,
    )


# ──────────────────────────────────────────────
# API-004: 특정 job 기준 저장소 clone 실행
# POST /api/repo/analysis/{job_id}/clone
# ──────────────────────────────────────────────
@router.post(
    "/api/repo/analysis/{job_id}/clone",
    response_model=CloneResponse,
    summary="특정 job 기준 저장소 clone 실행",
    description="job_id에 해당하는 저장소를 clone하고 분석 대상 파일만 남기도록 필터링한다.",
    responses={
        404: {"model": ErrorResponse, "description": "존재하지 않는 job_id"},
        408: {"model": ErrorResponse, "description": "Clone 제한 시간 초과"},
        409: {"model": ErrorResponse, "description": "이미 clone이 완료된 job"},
        413: {"model": ErrorResponse, "description": "파일 수/용량 제한 초과"},
        500: {"model": ErrorResponse, "description": "Clone 실행 오류 (브랜치 없음·저장소 접근 불가·네트워크 오류 등 git 오류는 모두 500)"},
    },
)
async def clone_repository(
    job_id: UUID,
    request: CloneRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> CloneResponse:
    """
    수동 재시작 또는 단계별 테스트를 위해 특정 job의 저장소 clone만 실행한다.
    """
    service = AnalysisService(db)
    return await service.clone_repository(job_id, request or CloneRequest())


# ──────────────────────────────────────────────
# API-008: 임시 clone 디렉토리 cleanup
# DELETE /api/repo/analysis/{job_id}/workspace
# ──────────────────────────────────────────────
@router.delete(
    "/api/repo/analysis/{job_id}/workspace",
    response_model=WorkspaceCleanupResponse,
    summary="임시 clone 디렉토리 cleanup",
    description="분석 실패 또는 수동 재시도 시 서버 내부 임시 clone 디렉토리를 삭제한다.",
    responses={
        404: {"model": ErrorResponse, "description": "존재하지 않는 job_id 또는 workspace 없음"},
        409: {"model": ErrorResponse, "description": "분석 파이프라인 진행 중 삭제 시도"},
        500: {"model": ErrorResponse, "description": "파일 시스템 cleanup 실패"},
    },
)
async def cleanup_workspace(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> WorkspaceCleanupResponse:
    """수동 cleanup 또는 재시도 준비를 위해 임시 clone 디렉토리를 삭제한다."""
    service = AnalysisService(db)
    return await service.cleanup_workspace(job_id)


# ──────────────────────────────────────────────
# API-003: 분석 작업 상태 및 메타데이터 조회
# GET /api/repo/analysis/{job_id}
# ──────────────────────────────────────────────
@router.get(
    "/api/repo/analysis/{job_id}",
    response_model=JobStatusResponse,
    summary="분석 작업 상태 및 메타데이터 조회",
    description="job_id에 해당하는 분석 작업의 현재 상태와 저장소 메타데이터를 반환한다.",
    responses={
        404: {"model": ErrorResponse, "description": "존재하지 않는 job_id"},
        500: {"model": ErrorResponse, "description": "서버 내부 오류"},
    },
)
async def get_job_status(
    job_id: UUID,
    current_user: Annotated[dict | None, Depends(get_current_user_optional)] = None,
    db: AsyncSession = Depends(get_db),
) -> JobStatusResponse:
    """
    폴링 방식으로 진행 상태를 확인할 때 사용한다.
    실시간 수신은 WebSocket(API-006)을 권장한다.
    """
    service = AnalysisService(db)
    user_id = UUID(current_user["sub"]) if current_user and "sub" in current_user else None
    return await service.get_job_status(job_id, current_user_id=user_id)


# ──────────────────────────────────────────────
# API-005: SSE 분석 진행 상태 이벤트 스트림
# GET /api/repo/analysis/{job_id}/events
# ──────────────────────────────────────────────
@router.get(
    "/api/repo/analysis/{job_id}/events",
    summary="분석 진행 상태 이벤트 스트림 수신 (SSE)",
    description="Server-Sent Events 방식으로 분석 파이프라인의 진행 상태를 실시간 스트리밍한다.",
    responses={
        404: {"model": ErrorResponse, "description": "존재하지 않는 job_id"},
        409: {"model": ErrorResponse, "description": "이미 완료/실패한 작업"},
        500: {"model": ErrorResponse, "description": "이벤트 큐 오류"},
    },
)
async def stream_analysis_events(
    job_id: UUID,
    request: Request,
    token: str | None = Query(default=None),
) -> StreamingResponse:
    """
    SSE(Server-Sent Events) 방식으로 분석 진행 상태를 실시간 스트리밍한다.

    클라이언트는 EventSource API로 연결하며,
    각 파이프라인 단계 전환 시마다 이벤트를 수신한다.
    status가 COMPLETED 또는 FAILED인 이벤트 수신 후 스트림이 종료된다.
    """
    ## private/team job은 권한이 있는 사용자만 스트림을 수신할 수 있다. (자체 PR 리뷰 B1)
    current_user_id = _user_id_from_token(token)
    # job 존재 여부 + 접근 권한 확인 (별도 세션 사용)
    async with async_session_factory() as session:
        service = AnalysisService(session)
        job_status_response = await service.get_job_status(
            job_id, current_user_id=current_user_id
        )

    # 이미 완료/실패한 작업인지 확인 (DB 기준)
    if job_status_response.data.status in (JobStatus.COMPLETED, JobStatus.FAILED):
        last_event = event_manager.get_last_event(str(job_id))
        # 만약 이벤트 캐시에 아직 종료 이벤트가 남아있다면, 에러를 던지지 않고 캐시를 내려보냄
        if not last_event or last_event.status not in (JobStatus.COMPLETED, JobStatus.FAILED):
            raise JobAlreadyDoneError()

    async def event_generator():
        """SSE 이벤트 스트림 제너레이터"""
        try:
            async for event in event_manager.subscribe(str(job_id)):
                # 클라이언트 연결이 끊겼는지 확인
                if await request.is_disconnected():
                    break

                # SSE 형식으로 데이터 전송
                event_data = event.model_dump_json()
                yield f"data: {event_data}\n\n"

                # 최종 상태 수신 시 스트림 종료
                if event.status in (JobStatus.COMPLETED, JobStatus.FAILED):
                    break
        except Exception as e:
            logger.error(f"SSE 스트림 오류 (job_id={job_id}): {e}")
            error_data = json.dumps({
                "error": "STREAM_ERROR",
                "message": str(e)
            })
            yield f"data: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Nginx 프록시 버퍼링 비활성화
        },
    )


# ──────────────────────────────────────────────
# API-007: 전체 분석 파이프라인 시작
# POST /api/repo/analysis/{job_id}/start
# ──────────────────────────────────────────────
@router.post(
    "/api/repo/analysis/{job_id}/start",
    response_model=PipelineStartResponse,
    status_code=202,
    summary="전체 분석 파이프라인 시작",
    description="clone이 완료된 job에 대해 전체 분석 파이프라인을 비동기 시작한다.",
    responses={
        404: {"model": ErrorResponse, "description": "존재하지 않는 job_id"},
        409: {"model": ErrorResponse, "description": "이미 파이프라인 실행 중"},
        422: {"model": ErrorResponse, "description": "clone 미완료 상태"},
        500: {"model": ErrorResponse, "description": "파이프라인 시작 오류"},
    },
)
async def start_pipeline(
    job_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> PipelineStartResponse:
    """
    Clone 완료 후 Code Map → Doc Generation → Onboarding Guide → Report 저장
    순서로 전체 분석 파이프라인을 비동기 시작한다.

    이 API는 POST /api/analysis 내부에서 자동 호출된다.
    clone 실패 후 수동 재시작 시에만 직접 호출한다.
    """
    service = AnalysisService(db)
    return await service.start_pipeline(job_id, background_tasks)


## 바이너리 파일 확장자 집합 — 미리보기 불가 파일 유형 정의
_BINARY_EXTENSIONS = frozenset({
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp",
    ".mp3", ".mp4", ".wav", ".avi", ".mov", ".mkv",
    ".zip", ".tar", ".gz", ".bz2", ".7z", ".rar",
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
    ".exe", ".dll", ".so", ".dylib", ".bin", ".wasm",
    ".ttf", ".otf", ".woff", ".woff2",
    ".db", ".sqlite", ".sqlite3",
    ".lock",
})

## 파일 크기 제한 (문자 수 기준)
_MAX_FILE_CHARS = 50_000

## 확장자 → 언어 매핑
_EXT_TO_LANGUAGE: dict[str, str] = {
    ".py": "python", ".js": "javascript", ".jsx": "jsx",
    ".ts": "typescript", ".tsx": "tsx",
    ".java": "java", ".kt": "kotlin", ".kts": "kotlin",
    ".go": "go", ".rs": "rust", ".cpp": "cpp", ".c": "c",
    ".cs": "csharp", ".rb": "ruby", ".php": "php",
    ".html": "html", ".css": "css", ".scss": "scss",
    ".json": "json", ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml", ".xml": "xml", ".md": "markdown",
    ".sh": "bash", ".sql": "sql",
}


def _detect_language(path: str) -> str | None:
    path_obj = Path(path)
    if path_obj.name.lower() == "dockerfile":
        return "dockerfile"
    return _EXT_TO_LANGUAGE.get(path_obj.suffix.lower())


def _read_file_safe(clone_root: Path, rel_path: str) -> tuple[str, bool]:
    """
    clone workspace 내 파일을 안전하게 읽어 (content, truncated) 튜플로 반환한다.
    UTF-8 실패 시 CP949 fallback을 시도한다.
    """
    target = (clone_root / rel_path).resolve()
    try:
        target.relative_to(clone_root.resolve())
    except ValueError:
        raise FilePathForbiddenError()

    for encoding in ("utf-8", "cp949", "latin-1"):
        try:
            text = target.read_text(encoding=encoding, errors="strict")
            break
        except (UnicodeDecodeError, LookupError):
            continue
    else:
        text = target.read_text(encoding="utf-8", errors="replace")

    truncated = len(text) > _MAX_FILE_CHARS
    if truncated:
        text = text[:_MAX_FILE_CHARS]
    return text, truncated


def _truncate_text(text: str) -> tuple[str, bool]:
    """문자열을 _MAX_FILE_CHARS 기준으로 잘라 (text, truncated)를 반환한다."""
    truncated = len(text) > _MAX_FILE_CHARS
    if truncated:
        text = text[:_MAX_FILE_CHARS]
    return text, truncated


def _build_file_content_response(
    clean_path: str, content: str, truncated: bool
) -> FileContentResponse:
    """파일 컨텐츠 응답 객체를 생성한다. (로컬·DB fallback 공통)"""
    lines = content.count("\n") + (1 if content and not content.endswith("\n") else 0)
    return FileContentResponse(
        data=FileContentData(
            path=clean_path,
            content=content,
            language=_detect_language(clean_path),
            lines=lines,
            truncated=truncated,
        )
    )


async def _read_db_fallback_content(
    db: AsyncSession, job_id: UUID, clean_path: str
) -> str | None:
    """
    DB CodeNode에서 파일 content를 복구 조회한다 (Issue #226).

    조회 실패(세션 오류 등)는 가용성 보강 목적상 치명적이지 않으므로
    경고 로그만 남기고 None을 반환하여 호출측이 404로 처리하게 한다.
    """
    try:
        repo = EmbedRepository(db)
        return await repo.get_file_content(job_id, clean_path)
    except Exception as exc:  # noqa: BLE001 - fallback은 어떤 예외든 흡수
        logger.warning(
            "[파일 fallback] DB 복구 조회 실패 (path=%s): %s", clean_path, exc
        )
        return None


# ──────────────────────────────────────────────
# API-FILE: job 기준 저장소 파일 컨텐츠 조회
# GET /api/repo/analysis/{job_id}/files/content
# ──────────────────────────────────────────────
@router.get(
    "/api/repo/analysis/{job_id}/files/content",
    response_model=FileContentResponse,
    summary="저장소 파일 컨텐츠 조회",
    description=(
        "분석 job의 clone workspace 내 특정 파일 내용을 텍스트로 반환한다. "
        "path traversal, 바이너리 파일, 파일 크기 초과를 안전하게 처리한다."
    ),
    responses={
        403: {"model": ErrorResponse, "description": "허용되지 않는 경로 (path traversal)"},
        404: {"model": ErrorResponse, "description": "존재하지 않는 job_id 또는 워크스페이스 미준비"},
        422: {"model": ErrorResponse, "description": "바이너리 파일"},
        500: {"model": ErrorResponse, "description": "파일 읽기 오류"},
    },
)
async def get_file_content(
    job_id: UUID,
    path: str = Query(..., description="저장소 내 상대 경로 (예: src/main.py)"),
    current_user: Annotated[dict | None, Depends(get_current_user_optional)] = None,
    db: AsyncSession = Depends(get_db),
) -> FileContentResponse:
    """
    job_id에 해당하는 clone workspace에서 path 파일의 텍스트 내용을 반환한다.

    - clone workspace 경로: {CLONE_BASE_DIR}/{job_id}/repo
    - path traversal은 403으로 차단한다.
    - 바이너리 확장자는 422로 차단한다.
    - 50,000자 초과 시 잘린 내용과 truncated=true를 반환한다.
    """
    ## job 존재 확인
    service = AnalysisService(db)
    from app.common import access
    access.touch_last_accessed(db, job_id)
    user_id = (
        UUID(current_user["sub"])
        if current_user and "sub" in current_user
        else None
    )
    await service.get_job_status(job_id, current_user_id=user_id)

    settings = get_settings()
    clone_root = (Path(settings.CLONE_BASE_DIR) / str(job_id) / "repo").resolve()

    ## path traversal 사전 차단: 절대 경로 또는 상위 디렉토리 참조 포함 시 거부
    ##  (clone workspace 존재 여부와 무관하게 항상 먼저 검사한다)
    clean_path = path.lstrip("/").replace("\\", "/")
    if ".." in clean_path.split("/"):
        raise FilePathForbiddenError()

    target = (clone_root / clean_path).resolve()
    try:
        target.relative_to(clone_root)
    except ValueError:
        raise FilePathForbiddenError()

    ## 바이너리 파일 차단 (확장자 기반 — FS 존재 여부와 무관)
    if Path(clean_path).suffix.lower() in _BINARY_EXTENSIONS:
        raise BinaryFileError()

    ## 1차: 로컬 clone workspace에서 직접 읽기
    if not clone_root.exists():
        logger.info("[get_file_content] 로컬 스냅샷 부재 감지, 재클론 복구 개시 (job_id=%s)", job_id)
        try:
            async with async_session_factory() as session:
                real_service = AnalysisService(session)
                await real_service.restore_workspace(job_id)
                await session.commit()
        except Exception as exc:
            logger.error("[get_file_content] 자동 재클론 복구 실패: %s", exc)
            raise WorkspaceNotReadyError() from exc

    if clone_root.exists() and target.exists() and target.is_file():
        content, truncated = await asyncio.to_thread(
            _read_file_safe, clone_root, clean_path
        )
        return _build_file_content_response(clean_path, content, truncated)

    ## 2차 방어 (Issue #226): 로컬 FS 누락 시 DB CodeNode content로 복구 fallback.
    ##  임베딩 누락/예외로 FILE 노드가 비어 있어도 가용성을 유지한다.
    fallback_content = await _read_db_fallback_content(db, job_id, clean_path)
    if fallback_content is not None:
        logger.warning(
            "[파일 fallback] 로컬 FS 미존재 → DB content 복구 (job=%s, path=%s)",
            job_id,
            clean_path,
        )
        content, truncated = _truncate_text(fallback_content)
        return _build_file_content_response(clean_path, content, truncated)

    ## 로컬·DB 모두 실패 → 기존과 동일하게 404
    raise WorkspaceNotReadyError(
        message=f"파일을 찾을 수 없습니다: {clean_path}"
    )
