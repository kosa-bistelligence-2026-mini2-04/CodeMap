"""
분석 작업 REST API 라우터 (Controller/진입점)

담당 API:
  - API-001: GET /api/list/analysis (전체 분석 이력 목록 조회)
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.list.schemas import (
    AnalysisJobItem,
    AnalysisJobListData,
    AnalysisJobListResponse,
    ErrorResponse,
)
from app.list.service import ListserviceDep


logger = logging.getLogger(__name__)
# ──────────────────────────────────────────────
# APIRouter 인스턴스 생성
# ──────────────────────────────────────────────
router = APIRouter(prefix="/api/list", tags=["Project List"])


def verify_authorization(authorization: Annotated[str | None, Header()] = None) -> None:
    """명세에 따라 Bearer 인증 헤더가 있는지 확인합니다."""
    if authorization is None or not authorization.startswith("Bearer ") or not authorization[7:].strip():
        raise HTTPException(
            status_code=401,
            detail={
                "code": 401,
                "errorCode": "UNAUTHORIZED",
                "message": "토큰이 누락되었거나 만료되었습니다.",
            },
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
    service: ListserviceDep,
    page: Annotated[int, Query(ge=1, description="조회할 페이지 번호")] = 1,
    limit: Annotated[int, Query(ge=1, description="페이지당 반환할 이력 수")] = 10,
) -> AnalysisJobListResponse:
    """PROJECT-LIST-API-001 명세의 분석 이력 목록 응답을 반환합니다."""
    try:
        result = await service.get_analysis_jobs(page=page, limit=limit)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "errorCode": "DATABASE_ERROR",
                "message": "데이터베이스 조회 중 오류가 발생했습니다.",
            },
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
