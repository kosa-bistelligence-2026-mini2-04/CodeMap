"""
커스텀 예외 및 FastAPI 예외 핸들러 모듈

API 명세서에 정의된 에러 코드(INVALID_REPO_URL, REPOSITORY_NOT_FOUND 등)에 대응하는
커스텀 예외 클래스와 FastAPI 전역 예외 핸들러를 제공한다.
"""

import logging
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


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
# ValidationFailedError
# ──────────────────────────────────────────────
class ValidationFailedError(CodeMapException):
    """
    GitHub API 호출 중 서브프로세스 또는 기타 에러 발생 시 (500)
    """

    def __init__(self, message: str = "GitHub API 호출 중 오류가 발생했습니다."):
        super().__init__(500, "VALIDATION_FAILED", message)


# ──────────────────────────────────────────────
# API-003: 상태 조회 관련 예외
# ──────────────────────────────────────────────
class JobNotFoundError(CodeMapException):
    """존재하지 않는 job_id로 조회 시 발생 (404)"""

    def __init__(self, message: str = "존재하지 않는 분석 작업입니다."):
        super().__init__(404, "JOB_NOT_FOUND", message)


class ParseResultNotFoundError(CodeMapException):
    """분석 결과(report_json)가 아직 생성되지 않았을 때 발생 (404)"""

    def __init__(self, message: str = "분석 결과가 아직 생성되지 않았습니다."):
        super().__init__(404, "PARSE_RESULT_NOT_FOUND", message)


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
# PROJECT-AUTH: 인증 관련 예외
# ──────────────────────────────────────────────
class UnauthorizedError(CodeMapException):
    """JWT 토큰 없음 / 만료 / 서명 불일치 (401)"""

    def __init__(self, message: str = "토큰이 누락되었거나 만료되었습니다."):
        super().__init__(401, "UNAUTHORIZED", message)


class InvalidCredentialsError(CodeMapException):
    """이메일 또는 비밀번호 불일치 (401)"""

    def __init__(self, message: str = "이메일 또는 비밀번호가 올바르지 않습니다."):
        super().__init__(401, "INVALID_CREDENTIALS", message)


class EmailAlreadyExistsError(CodeMapException):
    """이미 등록된 이메일로 가입 시도 (409)"""

    def __init__(self, message: str = "이미 사용 중인 이메일입니다."):
        super().__init__(409, "EMAIL_ALREADY_EXISTS", message)


class InvalidRefreshTokenError(CodeMapException):
    """Refresh Token 만료 또는 위조 (401)"""

    def __init__(self, message: str = "Refresh Token이 유효하지 않거나 만료되었습니다."):
        super().__init__(401, "INVALID_REFRESH_TOKEN", message)


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
            content=build_error_response(
                status_code=exc.status_code,
                message=exc.message,
                error_code=exc.error_code,
            ),
        )

    @app.exception_handler(HTTPException)
    async def fastapi_http_exception_handler(
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        """FastAPI HTTP 예외를 프로젝트 표준 에러 포맷으로 변환한다."""
        return _http_exception_to_response(exc)

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        """Starlette 라우팅 HTTP 예외를 프로젝트 표준 에러 포맷으로 변환한다."""
        return _http_exception_to_response(exc)

    def _http_exception_to_response(
        exc: HTTPException | StarletteHTTPException,
    ) -> JSONResponse:
        """HTTP 예외 공통 변환 결과를 JSON 응답으로 감싼다."""
        detail = exc.detail
        headers = getattr(exc, "headers", None)
        if isinstance(detail, dict) and _is_standard_error_response(detail):
            return JSONResponse(
                status_code=exc.status_code,
                content=detail,
                headers=headers,
            )

        return JSONResponse(
            status_code=exc.status_code,
            content=_build_http_exception_response(exc),
            headers=headers,
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        """요청 검증 오류를 프로젝트 표준 에러 포맷으로 변환한다."""
        first_error = exc.errors()[0] if exc.errors() else {}
        field = _format_validation_field(first_error.get("loc"))
        return JSONResponse(
            status_code=422,
            content=build_error_response(
                status_code=422,
                message="요청 형식이 올바르지 않습니다.",
                error_code="INVALID_REQUEST",
                detail=str(first_error.get("msg")) if first_error else None,
                field=field,
                retryable=False,
            ),
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """예상치 못한 예외를 처리하는 폴백 핸들러"""
        logger.exception("Unhandled exception", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content=build_error_response(
                status_code=500,
                message="서버 내부 오류가 발생했습니다.",
                error_code="INTERNAL_ERROR",
                retryable=True,
            ),
        )


def build_error_response(
    status_code: int,
    message: str,
    error_code: str,
    detail: str | None = None,
    field: str | None = None,
    retryable: bool | None = None,
) -> dict:
    """프로젝트 표준 에러 응답 본문을 생성한다."""
    return {
        "code": status_code,
        "message": message,
        "data": None,
        "error": {
            "code": error_code,
            "detail": detail,
            "field": field,
            "retryable": _default_retryable(status_code) if retryable is None else retryable,
        },
    }


def _is_standard_error_response(detail: dict) -> bool:
    """이미 표준 에러 응답 본문인지 확인한다."""
    return (
        "code" in detail
        and "message" in detail
        and "data" in detail
        and isinstance(detail.get("error"), dict)
    )


def _build_http_exception_response(exc: HTTPException | StarletteHTTPException) -> dict:
    """HTTPException 상세값을 표준 에러 응답 본문으로 변환한다."""
    detail = exc.detail
    if isinstance(detail, dict):
        error_val = detail.get("error")
        ## 외부 라이브러리나 커스텀 미들웨어 등이 HTTPException을 발생시키면서
        ## error 필드를 dict 형태로 내려보내는 특수 예외 상황에 대응하기 위한 방어적 분기 처리
        if isinstance(error_val, dict):
            error_code = error_val.get("code") or _default_error_code(exc.status_code)
            
            # detail과 error_val의 값을 명시적 존재 여부 및 is not None 기준으로 우선순위 적용
            error_detail = (
                detail.get("detail")
                if detail.get("detail") is not None
                else error_val.get("detail")
            )
            field = (
                detail.get("field")
                if detail.get("field") is not None
                else error_val.get("field")
            )
            
            if "retryable" in detail:
                retryable = detail.get("retryable")
            elif "retryable" in error_val:
                retryable = error_val.get("retryable")
            else:
                retryable = None
        else:
            error_code = error_val or detail.get("error_code") or _default_error_code(exc.status_code)
            error_detail = detail.get("detail")
            field = detail.get("field")
            retryable = detail.get("retryable")
        message = detail.get("message") or _default_error_message(exc.status_code)
    else:
        error_code = _default_error_code(exc.status_code)
        message = str(detail) if detail else _default_error_message(exc.status_code)
        error_detail = None
        field = None
        retryable = None

    return build_error_response(
        status_code=exc.status_code,
        message=message,
        error_code=str(error_code),
        detail=error_detail,
        field=field,
        retryable=retryable,
    )


def _default_retryable(status_code: int) -> bool:
    """상태 코드에 따른 기본 재시도 가능 여부를 반환한다."""
    return status_code == 408 or status_code >= 500


def _default_error_code(status_code: int) -> str:
    """상태 코드에 따른 기본 에러 코드를 반환한다."""
    error_codes = {
        400: "INVALID_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        405: "METHOD_NOT_ALLOWED",
        408: "REQUEST_TIMEOUT",
        409: "CONFLICT",
        413: "CONTENT_TOO_LARGE",
        422: "INVALID_REQUEST",
        500: "INTERNAL_ERROR",
    }
    return error_codes.get(status_code, "API_ERROR")


def _default_error_message(status_code: int) -> str:
    """상태 코드에 따른 기본 사용자 메시지를 반환한다."""
    messages = {
        400: "유효하지 않은 요청 파라미터입니다.",
        401: "인증이 필요합니다.",
        403: "접근 권한이 없습니다.",
        404: "요청한 리소스를 찾을 수 없습니다.",
        405: "허용되지 않은 HTTP 메서드입니다.",
        408: "요청 처리 시간이 초과되었습니다.",
        409: "요청한 리소스 상태와 충돌이 발생했습니다.",
        413: "요청한 콘텐츠 크기가 제한을 초과했습니다.",
        422: "요청 형식이 올바르지 않습니다.",
        500: "서버 내부 오류가 발생했습니다.",
    }
    return messages.get(status_code, "요청 처리 중 오류가 발생했습니다.")


def _format_validation_field(location: object) -> str | None:
    """요청 검증 오류 위치를 클라이언트가 읽기 쉬운 필드명으로 변환한다."""
    if not isinstance(location, (list, tuple)):
        return None
    filtered = [str(item) for item in location if item not in {"body", "query", "path", "header"}]
    return ".".join(filtered) if filtered else None


# ──────────────────────────────────────────────
# DOCS-GEN 도메인 예외 (DOCS_API_SPEC.md 기준)
# ──────────────────────────────────────────────
class RepoNotFoundError(CodeMapException):
    """저장소(repo_id)가 존재하지 않을 때 발생 (404)"""

    def __init__(self, message: str = "저장소를 찾을 수 없습니다."):
        super().__init__(404, "REPO_NOT_FOUND", message)


class DatabaseSaveFailedError(CodeMapException):
    """문서 DB 저장 중 오류 발생 시 (500)"""

    def __init__(self, message: str = "문서 저장 중 오류가 발생했습니다."):
        super().__init__(500, "DATABASE_SAVE_FAILED", message)


# ──────────────────────────────────────────────
# DOCS-GEN-API-002: 가이드북 생성 트리거 관련 예외
# ──────────────────────────────────────────────
class DocsAlreadyExistsError(CodeMapException):
    """가이드북이 이미 존재하고 force=false인 경우 (409)"""

    def __init__(self, message: str = "가이드북이 이미 존재합니다. 덮어쓰려면 force=true를 사용하세요."):
        super().__init__(409, "DOCS_ALREADY_EXISTS", message)


class DocsGenerationInProgressError(CodeMapException):
    """가이드북 생성이 이미 진행 중일 때 (409)"""

    def __init__(self, message: str = "가이드북 생성이 이미 진행 중입니다."):
        super().__init__(409, "DOCS_GENERATION_IN_PROGRESS", message)


class AnalysisNotCompletedError(CodeMapException):
    """RAG 파이프라인(Parse/Embed)이 완료되지 않았을 때 (422)"""

    def __init__(self, message: str = "분석 파이프라인이 아직 완료되지 않았습니다."):
        super().__init__(422, "ANALYSIS_NOT_COMPLETED", message)


class DocsGenerationFailedError(CodeMapException):
    """가이드북 생성 중 LLM 오류 발생 시 (500)"""

    def __init__(self, message: str = "가이드북 생성 중 오류가 발생했습니다."):
        super().__init__(500, "DOCS_GENERATION_FAILED", message)
