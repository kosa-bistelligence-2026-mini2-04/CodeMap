from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.core.schemas import ErrorResponse


class AnalysisJobItem(BaseModel):
    """분석 작업 목록의 단일 항목 DTO입니다."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    job_id: UUID = Field(alias="jobId", description="분석 작업 고유 ID")
    repo_url: str = Field(alias="repoUrl", description="GitHub 저장소 URL")
    branch: str = Field(description="분석 대상 브랜치")
    status: str = Field(description="작업 상태")
    progress: int = Field(ge=0, le=100, description="작업 진행률")
    failed_agent: Optional[str] = Field(default=None, alias="failedAgent", description="실패한 에이전트명")
    error_message: Optional[str] = Field(default=None, alias="errorMessage", description="실패 시 에러 메시지")
    created_at: datetime = Field(alias="createdAt", description="작업 생성 시각")
    updated_at: datetime = Field(alias="updatedAt", description="작업 최종 변경 시각")


class AnalysisJobListData(BaseModel):
    """분석 작업 목록 응답의 data DTO입니다."""

    model_config = ConfigDict(populate_by_name=True)

    total_count: int = Field(alias="totalCount", description="전체 분석 이력 수")
    page: int = Field(description="현재 페이지 번호")
    limit: int = Field(description="페이지당 반환 개수")
    jobs: list[AnalysisJobItem] = Field(description="분석 작업 목록")


class AnalysisJobListResponse(BaseModel):
    """PROJECT-LIST-API-001 성공 응답 DTO입니다."""

    code: int = Field(default=200, description="HTTP 상태 코드")
    message: str = Field(default="success", description="응답 메시지")
    data: AnalysisJobListData


class AnalysisJobDetailData(BaseModel):
    """분석 작업 상세 조회 응답의 data DTO입니다."""

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    job_id: UUID = Field(alias="jobId", description="분석 작업 고유 ID")
    repo_url: str = Field(alias="repoUrl", description="GitHub 저장소 URL")
    repo_name: str = Field(alias="repoName", description="저장소 이름")
    owner: str = Field(description="저장소 소유자")
    branch: str = Field(description="분석 대상 브랜치")
    status: str = Field(description="작업 상태")
    current_step: Optional[str] = Field(default=None, alias="currentStep", description="현재 분석 단계")
    progress: int = Field(ge=0, le=100, description="작업 진행률")
    message: Optional[str] = Field(default=None, description="사용자 표시용 상태 메시지")
    created_at: datetime = Field(alias="createdAt", description="작업 생성 시각")
    updated_at: datetime = Field(alias="updatedAt", description="작업 최종 변경 시각")


class AnalysisJobDetailResponse(BaseModel):
    """PROJECT-LIST-API-004 성공 응답 DTO입니다."""

    code: int = Field(default=200, description="HTTP 상태 코드")
    message: str = Field(default="success", description="응답 메시지")
    data: AnalysisJobDetailData


class AnalysisProgressMessage(BaseModel):
    """PROJECT-LIST-API-003 WebSocket 발행 메시지 DTO입니다."""

    jobId: UUID = Field(description="상태를 추적하는 분석 작업 고유 ID")
    status: str = Field(description="작업 상태")
    progress: int = Field(ge=0, le=100, description="작업 진행률")
    currentStep: str | None = Field(default=None, description="현재 실행 중인 분석 단계명")
    failedAgent: str | None = Field(default=None, description="실패 단계 또는 실패 에이전트")
    errorMessage: str | None = Field(default=None, description="실패 사유")


# ──────────────────────────────────────────────
# PreValidateRequest
# ──────────────────────────────────────────────
class PreValidateRequest(BaseModel):
    """
    PROJECT-LIST-API-002 요청 DTO
    """

    repo_url: str = Field(alias="repoUrl", description="검증할 GitHub 저장소 URL")
    branch: Optional[str] = Field(default=None, description="검증 대상 브랜치. 미입력 시 기본 브랜치 검증")


# ──────────────────────────────────────────────
# PreValidateData
# ──────────────────────────────────────────────
class PreValidateData(BaseModel):
    """
    PROJECT-LIST-API-002 검증 결과 데이터 DTO
    """

    model_config = ConfigDict(populate_by_name=True)

    is_valid: bool = Field(alias="isValid", description="분석 가능 여부 (제한 조건 이내인 경우 true)")
    file_count: int = Field(alias="fileCount", description="저장소 내의 대상 파일 수")
    total_size_kb: int = Field(alias="totalSizeKb", description="저장소 총 용량 (KB)")
    warning_message: Optional[str] = Field(default=None, alias="warningMessage", description="제한 조건 초과 시 경고 메시지")
    is_truncated: bool = Field(default=False, alias="isTruncated", description="GitHub Trees API 결과 누락 여부")


# ──────────────────────────────────────────────
# PreValidateResponse
# ──────────────────────────────────────────────
class PreValidateResponse(BaseModel):
    """
    PROJECT-LIST-API-002 성공 응답 DTO
    """

    code: int = Field(default=200, description="HTTP 상태 코드")
    message: str = Field(default="success", description="응답 메시지")
    data: PreValidateData
