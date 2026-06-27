from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from uuid import UUID


@dataclass(frozen=True)
class AnalysisJobListModel:
    """목록 조회 도메인에서 사용하는 분석 작업 내부 모델입니다."""

    job_id: UUID
    repo_url: str
    branch: str
    status: str
    progress: int
    failed_agent: Optional[str]
    error_message: Optional[str]
    visibility: str
    team_id: UUID | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class AnalysisJobDetailModel:
    """상세 조회 도메인에서 사용하는 분석 작업 내부 모델입니다."""

    job_id: UUID
    repo_url: str
    repo_name: str
    owner: str
    branch: str
    status: str
    current_step: Optional[str]
    progress: int
    message: Optional[str]
    visibility: str
    team_id: UUID | None
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class AnalysisJobStatusUpdateModel:
    """상태 저장 도메인에서 사용하는 분석 작업 내부 모델입니다."""

    job_id: UUID
    status: str
    current_step: Optional[str]
    progress: int
    updated_at: datetime
