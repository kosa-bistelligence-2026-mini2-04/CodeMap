from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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


class ErrorResponse(BaseModel):
    """PROJECT-LIST-API-001 에러 응답 DTO입니다."""

    code: int = Field(description="HTTP 상태 코드")
    errorCode: str = Field(description="에러 코드")
    message: str = Field(description="에러 메시지")


class AnalysisProgressMessage(BaseModel):
    """PROJECT-LIST-API-003 WebSocket 발행 메시지 DTO입니다."""

    jobId: UUID = Field(description="상태를 추적하는 분석 작업 고유 ID")
    status: str = Field(description="작업 상태")
    progress: int = Field(ge=0, le=100, description="작업 진행률")
    currentStep: str | None = Field(default=None, description="현재 실행 중인 분석 단계명")
    failedAgent: str | None = Field(default=None, description="실패 단계 또는 실패 에이전트")
    errorMessage: str | None = Field(default=None, description="실패 사유")


class ListValidateRequest(BaseModel):
    """저장소 사전 검증 요청 DTO입니다."""

    repo_url: str = Field(alias="repoUrl", description="GitHub 저장소 URL")
    branch: Optional[str] = Field(default=None, description="분석 대상 브랜치")


class ListValidateData(BaseModel):
    """저장소 사전 검증 결과 데이터 DTO입니다."""

    model_config = ConfigDict(populate_by_name=True)

    is_valid: bool = Field(alias="isValid", description="저장소 유효성 여부")
    file_count: int = Field(alias="fileCount", description="저장소 파일 수")
    total_size_kb: float = Field(alias="totalSizeKb", description="저장소 총 크기(KB)")
    warning_message: Optional[str] = Field(default=None, alias="warningMessage", description="경고 메시지")


class ListValidateResponse(BaseModel):
    """저장소 사전 검증 응답 DTO입니다."""

    code: int = Field(default=200, description="HTTP 상태 코드")
    message: str = Field(default="success", description="응답 메시지")
    data: ListValidateData
