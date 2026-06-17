from typing import Annotated

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from app.repo.schemas import (
    ApiErrorResponse,
    ApiResponse,
    RepoValidateData,
    RepoValidateRequest,
)
from app.repo.service import RepoApiError, RepoServiceDep


router = APIRouter(prefix="/api/repo", tags=["repo"])


@router.post(
    "/validate",
    response_model=ApiResponse,
    responses={
        400: {"model": ApiErrorResponse},
        404: {"model": ApiErrorResponse},
        500: {"model": ApiErrorResponse},
    },
    summary="GitHub URL 형식 및 접근 가능 여부 검증",
)
async def validate_repo(
    request: Annotated[RepoValidateRequest, Body()],
    repo_service: RepoServiceDep,
):
    try:
        identity = await repo_service.validate_github_url(request.repo_url)
    except RepoApiError as exc:
        return _error_response(exc)

    data = RepoValidateData(
        valid=True,
        repoName=identity.repo_name,
        owner=identity.owner,
        defaultBranch=identity.default_branch,
        isPrivate=identity.is_private,
    )
    return ApiResponse(code=200, message="success", data=data)


def _error_response(exc: RepoApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "detail": exc.detail,
            }
        },
    )
