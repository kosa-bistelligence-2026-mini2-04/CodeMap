'''
분석 작업 REST API 라우터 (Controller/진입점)

담당 API:
  - API-001: GET /api/list/analysis (전체 분석 이력 목록 조회)
  - API-002: POST /api/list/validate (저장소 파일수/용량 사전 검증)
'''
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query

from app.core.exceptions import CodeMapException, ValidationFailedError
from app.list.schemas import (
    AnalysisJobItem,
    AnalysisJobListData,
    AnalysisJobListResponse,
    ErrorResponse,
    ListValidateRequest,
    ListValidateResponse,
)
from app.list.service import ListserviceDep


logger = logging.getLogger(__name__)




# ──────────────────────────────────────────────
# APIRouter 인스턴스 생성 및 라우터 정의
# ──────────────────────────────────────────────
router = APIRouter(prefix="/api/list", tags=["Project List"])


# ──────────────────────────────────────────────
# Bearer 인증 토큰 검증 함수
# ──────────────────────────────────────────────
def verify_authorization(authorization: Annotated[str | None, Header()] = None) -> None:
    '''명세에 따라 Bearer 인증 헤더가 있는지 확인합니다.'''
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
# API-001: 전체 분석 이력 목록 조회 (GET /api/list/analysis)
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
    '''PROJECT-LIST-API-001 명세의 분석 이력 목록 응답을 반환합니다.'''
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


# ──────────────────────────────────────────────
# API-002: 저장소 파일수/용량 사전 검증 (POST /api/list/validate)
# ──────────────────────────────────────────────
@router.post(
    "/validate",
    response_model=ListValidateResponse,
    summary="저장소 파일수 및 용량 사전 검증",
    description="Git Clone 및 정밀 분석을 시작하기 전에 대상 GitHub 저장소의 파일 수 및 용량을 사전에 검증합니다.",
    responses={
        400: {"model": ErrorResponse, "description": "잘못된 저장소 URL"},
        401: {"model": ErrorResponse, "description": "인증 토큰 누락 또는 만료"},
        404: {"model": ErrorResponse, "description": "저장소를 찾을 수 없음"},
        500: {"model": ErrorResponse, "description": "사전 검증 실패 또는 시간 초과"},
    },
)
async def validate_repository(
    _: Annotated[None, Depends(verify_authorization)],
    request: ListValidateRequest,
    service: ListserviceDep,
) -> ListValidateResponse:
    '''
    사용자가 지정한 GitHub 저장소의 파일 개수 및 총 크기를 사전 검증합니다.
    '''
    try:
        result = await service.validate_repository(
            repo_url=request.repo_url,
            branch=request.branch
        )
    except ValidationFailedError as exc:
        ## tenacity 3회 재시도 실패 등 검증 실패(500) 상황 처리
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "errorCode": "VALIDATION_FAILED",
                "message": exc.message,
                "data": exc.data
            }
        )
    except CodeMapException:
        raise
    except HTTPException:
        raise
    except Exception as exc:
        ## 기타 예기치 못한 에러
        raise HTTPException(
            status_code=500,
            detail={
                "code": 500,
                "errorCode": "VALIDATION_FAILED",
                "message": "저장소 검증 중 예상치 못한 오류가 발생했습니다.",
                "data": {
                    "isValid": False,
                    "fileCount": 0,
                    "totalSizeKb": 0,
                    "warningMessage": str(exc)
                }
            }
        ) from exc

    return ListValidateResponse(
        code=200,
        message="success",
        data=result
    )
