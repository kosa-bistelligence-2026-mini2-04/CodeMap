from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """표준 에러 응답의 상세 정보 DTO입니다."""

    code: str = Field(description="도메인 에러 코드")
    detail: str | None = Field(default=None, description="디버깅용 안전 상세 정보")
    field: str | None = Field(default=None, description="오류가 발생한 요청 필드")
    retryable: bool = Field(description="자동 재시도 가능 여부")


class ErrorResponse(BaseModel):
    """ERROR_HANDLING.md 기준의 표준 에러 응답 DTO입니다."""

    code: int = Field(description="HTTP 상태 코드")
    message: str = Field(description="사용자 표시용 에러 메시지")
    data: None = Field(default=None, description="에러 응답에서는 항상 null")
    error: ErrorDetail
