"""
Pydantic DTO(Data Transfer Object) 스키마 모듈

API 요청/응답의 데이터 유효성 검증 및 직렬화를 담당한다.
API 명세서에 정의된 모든 필드명, 타입, 필수 여부를 정확히 반영한다.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ──────────────────────────────────────────────
# Enum 정의: 작업 상태
# ──────────────────────────────────────────────
class JobStatus(str, Enum):
    """분석 작업의 상태를 정의하는 열거형"""
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


# ──────────────────────────────────────────────
# Enum 정의: 파이프라인 단계
# ──────────────────────────────────────────────
class PipelineStage(str, Enum):
    """분석 파이프라인의 각 단계를 정의하는 열거형"""
    CLONE = "CLONE"           # 저장소 복제 (0~20%)
    CODE_MAP = "CODE_MAP"     # 코드 구조 분석 (21~50%)
    DOC_GEN = "DOC_GEN"       # 문서 자동 생성 (51~70%)
    ONBOARDING = "ONBOARDING" # 온보딩 가이드 생성 (71~90%)
    REPORT = "REPORT"         # 최종 결과 DB 저장 (91~100%)


# ──────────────────────────────────────────────
# API-001: 프로젝트 등록 요청 DTO
# ──────────────────────────────────────────────
class AnalysisRequest(BaseModel):
    """
    POST /api/repo/analysis 요청 본문 스키마

    GitHub 저장소 URL과 분석 대상 브랜치를 전달받는다.
    """
    # 분석할 GitHub 저장소 URL (필수)
    repoUrl: str = Field(
        ...,
        description=(
            "분석할 GitHub 저장소 URL"
            " (https://github.com/owner/repo 형식)"
        ),
        examples=[
            "https://github.com/username/my-project"
        ],
    )

    # 분석 대상 브랜치 (선택, 미입력 시 기본 브랜치 사용)
    branch: Optional[str] = Field(
        default=None,
        description=(
            "분석 대상 브랜치."
            " 미입력 시 저장소 기본 브랜치를 사용"
        ),
        examples=["main"],
    )


# ──────────────────────────────────────────────
# API-002: GitHub URL 검증 요청/응답 DTO
# ──────────────────────────────────────────────
class RepoValidateRequest(BaseModel):
    """
    POST /api/repo/validate 요청 본문 스키마

    Clone 이전 단계에서 GitHub 저장소 URL 형식과 접근 가능 여부를
    검증하기 위한 요청 DTO이다.
    """
    repoUrl: str = Field(
        ...,
        description="검증할 GitHub 저장소 URL",
        examples=["https://github.com/username/my-project"],
    )


class RepoValidateData(BaseModel):
    """API-002 성공 응답의 data 필드 스키마"""
    valid: bool = Field(description="검증 통과 여부")
    repoName: str = Field(description="저장소 이름")
    owner: str = Field(description="저장소 소유자")
    defaultBranch: str = Field(description="저장소 기본 브랜치")
    isPrivate: bool = Field(description="private 저장소 여부")


class RepoValidateResponse(BaseModel):
    """
    POST /api/repo/validate 성공 응답 스키마 (200 OK)
    """
    code: int = Field(default=200, description="HTTP 상태 코드")
    message: str = Field(default="success", description="응답 메시지")
    data: RepoValidateData



# ──────────────────────────────────────────────
# API-001: 프로젝트 등록 응답 내부 데이터 DTO
# ──────────────────────────────────────────────
class AnalysisData(BaseModel):
    """API-001 성공 응답의 data 필드 스키마"""
    jobId: UUID = Field(
        description="발급된 분석 작업 고유 ID"
    )
    repoName: str = Field(
        description="저장소 이름"
    )
    owner: str = Field(
        description="저장소 소유자"
    )
    branch: str = Field(
        description="분석 대상 브랜치"
    )
    status: JobStatus = Field(
        description="초기 상태: IN_PROGRESS"
    )
    createdAt: datetime = Field(
        description="작업 생성 시각"
    )


class AnalysisResponse(BaseModel):
    """
    POST /api/analysis 성공 응답 스키마 (201 Created)
    """
    code: int = Field(default=201, description="HTTP 상태 코드")
    message: str = Field(default="created", description="응답 메시지")
    data: AnalysisData


# ──────────────────────────────────────────────
# API-003: 분석 작업 상태 조회 응답 DTO
# ──────────────────────────────────────────────
class JobStatusData(BaseModel):
    """API-003 성공 응답의 data 필드 스키마"""
    jobId: UUID = Field(
        description="분석 작업 고유 ID"
    )
    repoName: str = Field(
        description="저장소 이름"
    )
    owner: str = Field(
        description="저장소 소유자"
    )
    branch: str = Field(
        description="분석 대상 브랜치"
    )
    clonePath: str = Field(
        description="서버 내 임시 clone 경로"
    )
    status: JobStatus = Field(
        description=(
            "현재 상태:"
            " IN_PROGRESS / COMPLETED / FAILED"
        )
    )
    createdAt: datetime = Field(
        description="작업 생성 시각"
    )
    updatedAt: datetime = Field(
        description="마지막 상태 변경 시각"
    )


class JobStatusResponse(BaseModel):
    """
    GET /api/repo/analysis/{job_id} 성공 응답 스키마 (200 OK)
    """
    code: int = Field(default=200, description="HTTP 상태 코드")
    message: str = Field(default="success", description="응답 메시지")
    data: JobStatusData


# ──────────────────────────────────────────────
# API-005 & API-006: SSE/WebSocket 이벤트 DTO
# ──────────────────────────────────────────────
class ProgressEvent(BaseModel):
    """
    SSE 및 WebSocket으로 전송되는 진행 상태 이벤트 스키마

    각 파이프라인 단계 전환 시마다 클라이언트에 push되는 데이터 구조.
    """
    stage: PipelineStage = Field(
        description="현재 단계"
        " (CLONE / CODE_MAP / DOC_GEN"
        " / ONBOARDING / REPORT)"
    )
    status: JobStatus = Field(
        description="단계 상태"
        " (IN_PROGRESS / COMPLETED / FAILED)"
    )
    progress: int = Field(
        ge=0, le=100,
        description="전체 진행률 (0 ~ 100)"
    )
    message: str = Field(
        description="진행 상태 메시지"
    )
    timestamp: datetime = Field(
        description="이벤트 발생 시각"
    )


# ──────────────────────────────────────────────
# API-007: 파이프라인 시작 응답 DTO
# ──────────────────────────────────────────────
class PipelineStartData(BaseModel):
    """API-007 성공 응답의 data 필드 스키마"""
    jobId: UUID = Field(
        description="분석 작업 고유 ID"
    )
    status: JobStatus = Field(
        description="파이프라인 시작 상태: IN_PROGRESS"
    )
    startedAt: datetime = Field(
        description="파이프라인 시작 시각"
    )


class PipelineStartResponse(BaseModel):
    """
    POST /api/repo/analysis/{job_id}/start 성공 응답 스키마 (202 Accepted)
    """
    code: int = Field(default=202, description="HTTP 상태 코드")
    message: str = Field(default="accepted", description="응답 메시지")
    data: PipelineStartData


# ──────────────────────────────────────────────
# 공통 에러 응답 DTO
# ──────────────────────────────────────────────
class ErrorResponse(BaseModel):
    """통일된 에러 응답 스키마"""
    code: int = Field(
        description="HTTP 상태 코드"
    )
    error: str = Field(
        description="에러 코드 (예: INVALID_REPO_URL)"
    )
    message: str = Field(
        description="에러 메시지"
    )
