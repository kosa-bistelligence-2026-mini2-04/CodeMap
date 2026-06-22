"""
분석 작업 REST API 라우터 (Controller/진입점)

담당 API:
  - API-001: GET /api/list/analysis (전체 분석 이력 목록 조회)
"""
import logging
from secrets import compare_digest
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.core.config import get_settings
from app.core.exceptions import build_error_response
from app.list.schemas import (
    AnalysisJobDetailData,
    AnalysisJobDetailResponse,
    AnalysisJobItem,
    AnalysisJobListData,
    AnalysisJobListResponse,
    AnalysisJobStatusUpdateData,
    AnalysisJobStatusUpdateRequest,
    AnalysisJobStatusUpdateResponse,
    ErrorResponse,
    PreValidateRequest,
    PreValidateResponse,
)
from app.list.service import ListServiceDep


logger = logging.getLogger(__name__)
# ──────────────────────────────────────────────
# APIRouter 인스턴스 생성
# ──────────────────────────────────────────────
router = APIRouter(prefix="/api/list", tags=["Project List"])

ALLOWED_STATUS_VALUES = {"queued", "running", "completed", "failed"}


def verify_authorization(authorization: Annotated[str | None, Header()] = None) -> None:
    """명세에 따라 Bearer 인증 헤더가 있는지 확인합니다."""
    if authorization is None or not authorization.startswith("Bearer ") or not authorization[7:].strip():
        raise HTTPException(
            status_code=401,
            detail=build_error_response(
                status_code=401,
                message="토큰이 누락되었거나 만료되었습니다.",
                error_code="UNAUTHORIZED",
            ),
        )


def verify_service_authorization(authorization: Annotated[str | None, Header()] = None) -> None:
    """내부 서버 간 호출용 서비스 토큰이 설정값과 일치하는지 확인합니다."""
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail=build_error_response(
                status_code=401,
                message="내부 서비스 토큰이 누락되었거나 올바르지 않습니다.",
                error_code="UNAUTHORIZED",
            ),
        )

    token = authorization[7:].strip()
    expected_token = get_settings().SERVICE_TOKEN.strip()
    if not token or not expected_token or not compare_digest(token, expected_token):
        raise HTTPException(
            status_code=401,
            detail=build_error_response(
                status_code=401,
                message="내부 서비스 토큰이 누락되었거나 올바르지 않습니다.",
                error_code="UNAUTHORIZED",
            ),
        )


# ──────────────────────────────────────────────
# API-001: 전체 분석 이력 목록 조회
# GET /api/list/analysis
# ──────────────────────────────────────────────
@router.get(
    "/analysis",
    response_model=AnalysisJobListResponse,
    summary="전체 분석 이력 목록 조회",
    description="사용자가 이전에 분석을 시도했거나 완료한 저장소 분석 작업 목록을 페이지 단위로 조회합니다.",
    responses={
        401: {"model": ErrorResponse, "description": "인증 토큰 누락 또는 만료"},
        500: {"model": ErrorResponse, "description": "DB 조회 중 오류"},
    },
)
async def get_analysis_jobs(
    _: Annotated[None, Depends(verify_authorization)],
    service: ListServiceDep,
    page: Annotated[int, Query(ge=1, description="조회할 페이지 번호")] = 1,
    limit: Annotated[int, Query(ge=1, description="페이지당 반환할 이력 수")] = 10,
) -> AnalysisJobListResponse:
    """PROJECT-LIST-API-001 명세의 분석 이력 목록 응답을 반환합니다."""
    try:
        result = await service.get_analysis_jobs(page=page, limit=limit)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=build_error_response(
                status_code=500,
                message="데이터베이스 조회 중 오류가 발생했습니다.",
                error_code="DATABASE_ERROR",
                retryable=True,
            ),
        ) from exc

    return AnalysisJobListResponse(
        code=200,
        message="success",
        data=AnalysisJobListData(
            totalCount=result.total_count,
            page=result.page,
            limit=result.limit,
            jobs=[AnalysisJobItem.model_validate(job) for job in result.jobs],
        ),
    )


# API-004: 분석 이력 상세 조회
# GET /api/list/analysis/{job_id}
@router.get(
    "/analysis/{job_id}",
    response_model=AnalysisJobDetailResponse,
    summary="분석 이력 상세 조회",
    description="목록에서 선택한 분석 job의 상세 상태와 메타데이터를 조회합니다.",
    responses={
        400: {"model": ErrorResponse, "description": "job_id UUID 형식 오류"},
        401: {"model": ErrorResponse, "description": "인증 토큰 누락 또는 만료"},
        404: {"model": ErrorResponse, "description": "분석 작업 없음"},
        500: {"model": ErrorResponse, "description": "DB 조회 중 오류"},
    },
)
async def get_analysis_job_detail(
    job_id: str,
    _: Annotated[None, Depends(verify_authorization)],
    service: ListServiceDep,
) -> AnalysisJobDetailResponse:
    """PROJECT-LIST-API-004 명세에 맞춰 분석 작업 상세 응답을 반환합니다."""
    try:
        job_uuid = UUID(job_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=build_error_response(
                status_code=400,
                message="job_id가 UUID 형식이 아닙니다.",
                error_code="INVALID_JOB_ID",
                field="job_id",
            ),
        ) from exc

    try:
        result = await service.get_analysis_job_detail(job_id=job_uuid)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=build_error_response(
                status_code=500,
                message="데이터베이스 조회 중 오류가 발생했습니다.",
                error_code="DATABASE_ERROR",
                retryable=True,
            ),
        ) from exc

    if result.job is None:
        raise HTTPException(
            status_code=404,
            detail=build_error_response(
                status_code=404,
                message="해당 job_id가 존재하지 않습니다.",
                error_code="JOB_NOT_FOUND",
                field="job_id",
            ),
        )

    return AnalysisJobDetailResponse(
        code=200,
        message="success",
        data=AnalysisJobDetailData.model_validate(result.job),
    )


# API-006: 분석 job 상태 저장
# PATCH /api/list/analysis/{job_id}/status
@router.patch(
    "/analysis/{job_id}/status",
    response_model=AnalysisJobStatusUpdateResponse,
    summary="분석 job 상태 저장",
    description="파이프라인 내부에서 분석 job 상태, 단계, 진행률, 실패 메시지를 저장합니다.",
    responses={
        400: {"model": ErrorResponse, "description": "상태 또는 진행률 검증 오류"},
        401: {"model": ErrorResponse, "description": "내부 서비스 토큰 누락 또는 만료"},
        404: {"model": ErrorResponse, "description": "분석 작업 없음"},
        500: {"model": ErrorResponse, "description": "DB 저장 중 오류"},
    },
)
async def update_analysis_job_status(
    job_id: str,
    request: AnalysisJobStatusUpdateRequest,
    _: Annotated[None, Depends(verify_service_authorization)],
    service: ListServiceDep,
) -> AnalysisJobStatusUpdateResponse:
    """PROJECT-LIST-API-006 명세에 맞춰 분석 작업 상태를 저장합니다."""
    try:
        job_uuid = UUID(job_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=build_error_response(
                status_code=400,
                message="job_id가 UUID 형식이 아닙니다.",
                error_code="INVALID_JOB_ID",
                field="job_id",
            ),
        ) from exc

    if request.status not in ALLOWED_STATUS_VALUES:
        raise HTTPException(
            status_code=400,
            detail=build_error_response(
                status_code=400,
                message="허용되지 않은 status 값입니다.",
                error_code="INVALID_STATUS",
                field="status",
            ),
        )

    if request.progress < 0 or request.progress > 100:
        raise HTTPException(
            status_code=400,
            detail=build_error_response(
                status_code=400,
                message="progress는 0-100 범위여야 합니다.",
                error_code="INVALID_PROGRESS",
                field="progress",
            ),
        )

    try:
        result = await service.update_analysis_job_status(
            job_id=job_uuid,
            status=request.status,
            current_step=request.current_step,
            progress=request.progress,
            message=request.message,
            error_message=request.error_message,
        )
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=build_error_response(
                status_code=500,
                message="상태 저장 중 오류가 발생했습니다.",
                error_code="DATABASE_ERROR",
                retryable=True,
            ),
        ) from exc

    if result.job is None:
        raise HTTPException(
            status_code=404,
            detail=build_error_response(
                status_code=404,
                message="해당 job_id가 존재하지 않습니다.",
                error_code="JOB_NOT_FOUND",
                field="job_id",
            ),
        )

    return AnalysisJobStatusUpdateResponse(
        code=200,
        message="success",
        data=AnalysisJobStatusUpdateData.model_validate(result.job),
    )
# ──────────────────────────────────────────────
# API-002: 클론 전 저장소 파일 수 및 용량 사전 검증
# POST /api/list/validate
# ──────────────────────────────────────────────
@router.post(
    "/validate",
    response_model=PreValidateResponse,
    summary="클론 전 저장소 파일 수 및 용량 사전 검증",
    description="본격적인 Git Clone 및 분석 파이프라인 시작 전에, 대상 저장소의 파일 개수 및 용량이 제한 조건을 준수하는지 검증합니다.",
    responses={
        400: {"model": ErrorResponse, "description": "GitHub URL 형식 오류"},
        401: {"model": ErrorResponse, "description": "인증 토큰 누락 또는 만료"},
        404: {"model": ErrorResponse, "description": "저장소가 존재하지 않거나 비공개"},
        500: {"model": ErrorResponse, "description": "GitHub API 호출 중 오류 발생"},
    },
)
async def validate_repository(
    request: PreValidateRequest,
    _: Annotated[None, Depends(verify_authorization)],
    service: ListServiceDep,
) -> PreValidateResponse:
    """PROJECT-LIST-API-002 명세의 사전 검증 결과를 반환합니다."""
    return await service.validate_repository(
        repo_url=request.repo_url,
        branch=request.branch,
    )

