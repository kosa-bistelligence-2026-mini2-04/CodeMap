"""
커스텀 예외 및 FastAPI 예외 핸들러 모듈

API 명세서에 정의된 에러 코드(INVALID_REPO_URL, REPOSITORY_NOT_FOUND 등)에 대응하는
커스텀 예외 클래스와 FastAPI 전역 예외 핸들러를 제공한다.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


# ──────────────────────────────────────────────
# 기본 예외 클래스 (모든 커스텀 예외의 부모)
# ──────────────────────────────────────────────
class CodeMapException(Exception):
    """CodeMap 애플리케이션 기본 예외 클래스"""

    def __init__(self, status_code: int, error_code: str, message: str):
        self.status_code = status_code
        self.error_code = error_code
        self.message = message
        super().__init__(message)


# ──────────────────────────────────────────────
# API-001: 프로젝트 등록 관련 예외
# ──────────────────────────────────────────────
class InvalidRepoUrlError(CodeMapException):
    """GitHub URL 형식이 올바르지 않을 때 발생 (400)"""

    def __init__(self, message: str = "GitHub URL 형식이 올바르지 않습니다."):
        super().__init__(400, "INVALID_REPO_URL", message)


class RepositoryNotFoundError(CodeMapException):
    """저장소가 없거나 접근 불가할 때 발생 (404)"""

    def __init__(self, message: str = "저장소가 없거나 접근이 불가합니다."):
        super().__init__(404, "REPOSITORY_NOT_FOUND", message)


class CloneTimeoutError(CodeMapException):
    """Clone 제한 시간 초과 시 발생 (408)"""

    def __init__(self, message: str = "Clone 제한 시간이 초과되었습니다."):
        super().__init__(408, "CLONE_TIMEOUT", message)


class AlreadyInProgressError(CodeMapException):
    """동일 저장소 분석이 이미 진행 중일 때 발생 (409)"""

    def __init__(self, message: str = "동일 저장소에 대한 분석이 이미 진행 중입니다."):
        super().__init__(409, "ALREADY_IN_PROGRESS", message)


class FileLimitExceededError(CodeMapException):
    """Clone 후 실제 파일 수 또는 용량 제한 초과 시 발생 (413)"""

    def __init__(self, message: str = "파일 수 또는 용량 제한을 초과했습니다."):
        super().__init__(413, "FILE_LIMIT_EXCEEDED", message)


class RepoLimitExceededError(CodeMapException):
    """Clone 전 GitHub API 기준 용량 초과 시 발생 (422)"""

    def __init__(self, message: str = "GitHub API 기준 저장소 용량 제한을 초과했습니다."):
        super().__init__(422, "REPO_LIMIT_EXCEEDED", message)


class CloneFailedError(CodeMapException):
    """Clone 중 subprocess 오류 발생 시 (500)"""

    def __init__(self, message: str = "저장소 Clone 중 오류가 발생했습니다."):
        super().__init__(500, "CLONE_FAILED", message)


class WorkspaceCleanupFailedError(CodeMapException):
    """임시 디렉토리 삭제 실패 시 (500, 내부 알람용)"""

    def __init__(self, message: str = "임시 작업 디렉토리 정리에 실패했습니다."):
        super().__init__(500, "WORKSPACE_CLEANUP_FAILED", message)


# ──────────────────────────────────────────────
# API-003: 상태 조회 관련 예외
# ──────────────────────────────────────────────
class JobNotFoundError(CodeMapException):
    """존재하지 않는 job_id로 조회 시 발생 (404)"""

    def __init__(self, message: str = "존재하지 않는 분석 작업입니다."):
        super().__init__(404, "JOB_NOT_FOUND", message)


class InternalError(CodeMapException):
    """서버 내부 오류 (500)"""

    def __init__(self, message: str = "서버 내부 오류가 발생했습니다."):
        super().__init__(500, "INTERNAL_ERROR", message)


# ──────────────────────────────────────────────
# API-005: SSE 관련 예외
# ──────────────────────────────────────────────
class JobAlreadyDoneError(CodeMapException):
    """이미 COMPLETED/FAILED 상태인 job에 SSE/WS 연결 시도 시 발생 (409)"""

    def __init__(self, message: str = "이미 완료되었거나 실패한 분석 작업입니다."):
        super().__init__(409, "JOB_ALREADY_DONE", message)


class StreamError(CodeMapException):
    """이벤트 큐 오류 발생 시 (500)"""

    def __init__(self, message: str = "이벤트 스트림 오류가 발생했습니다."):
        super().__init__(500, "STREAM_ERROR", message)


# ──────────────────────────────────────────────
# API-007: 파이프라인 관련 예외
# ──────────────────────────────────────────────
class PipelineAlreadyRunningError(CodeMapException):
    """이미 파이프라인이 실행 중인 job에 시작 요청 시 발생 (409)"""

    def __init__(self, message: str = "해당 작업의 파이프라인이 이미 실행 중입니다."):
        super().__init__(409, "PIPELINE_ALREADY_RUNNING", message)


class CloneNotCompletedError(CodeMapException):
    """Clone이 완료되지 않은 상태에서 파이프라인 시작 요청 시 발생 (422)"""

    def __init__(self, message: str = "저장소 Clone이 아직 완료되지 않았습니다."):
        super().__init__(422, "CLONE_NOT_COMPLETED", message)


class PipelineStartFailedError(CodeMapException):
    """파이프라인 시작 중 오류 발생 시 (500)"""

    def __init__(self, message: str = "분석 파이프라인 시작에 실패했습니다."):
        super().__init__(500, "PIPELINE_START_FAILED", message)


# ──────────────────────────────────────────────
# FastAPI 전역 예외 핸들러 등록 함수
# ──────────────────────────────────────────────
def register_exception_handlers(app: FastAPI) -> None:
    """
    FastAPI 앱에 커스텀 예외 핸들러를 등록한다.

    모든 CodeMapException 하위 예외를 잡아서 통일된 JSON 에러 포맷으로 응답한다.
    """

    @app.exception_handler(CodeMapException)
    async def codemap_exception_handler(
        request: Request, exc: CodeMapException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "code": exc.status_code,
                "error": exc.error_code,
                "message": exc.message,
            },
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """예상치 못한 예외를 처리하는 폴백 핸들러"""
        import logging
        logger = logging.getLogger(__name__)
        logger.exception("Unhandled exception", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "code": 500,
                "error": "INTERNAL_ERROR",
                "message": "서버 내부 오류가 발생했습니다.",
            },
        )
