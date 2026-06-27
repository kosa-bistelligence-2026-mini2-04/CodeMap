"""
Pydantic DTO(Data Transfer Object) 스키마 모듈

API 요청/응답의 데이터 유효성 검증 및 직렬화를 담당한다.
API 명세서에 정의된 모든 필드명, 타입, 필수 여부를 정확히 반영한다.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, JsonValue

from app.common.schemas import ErrorResponse
from app.pipeline.schemas import JobStatus, PipelineStage, ProgressEvent


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

    model: str = Field(default="auto", description="분석 모델 정책. 기본값은 자동 선택")
    forceRefresh: bool = Field(default=False, description="기존 스냅샷을 무시하고 새로 분석")


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
# API-004: 특정 job 기준 저장소 clone 요청/응답 DTO
# ──────────────────────────────────────────────
class CloneRequest(BaseModel):
    """
    POST /api/repo/analysis/{job_id}/clone 요청 본문 스키마

    timeoutSeconds 미입력 시 기본 300초를 사용한다.
    """
    timeoutSeconds: int = Field(
        default=300,
        ge=1,
        le=1800,
        description="clone 제한 시간(초)",
        examples=[300],
    )


class CloneData(BaseModel):
    """API-004 성공 응답의 data 필드 스키마"""
    jobId: UUID = Field(description="분석 작업 고유 ID")
    clonePath: str = Field(description="작업 기준 논리 경로 (jobs/{jobId})")
    fileCount: int = Field(description="필터링 후 분석 대상 파일 수")
    sizeKb: int = Field(description="필터링 후 총 용량(KB)")


class CloneResponse(BaseModel):
    """
    POST /api/repo/analysis/{job_id}/clone 성공 응답 스키마 (200 OK)
    """
    code: int = Field(default=200, description="HTTP 상태 코드")
    message: str = Field(default="success", description="응답 메시지")
    data: CloneData


# ──────────────────────────────────────────────
# API-008: 임시 clone 디렉토리 cleanup 응답 DTO
# ──────────────────────────────────────────────
class WorkspaceCleanupData(BaseModel):
    """API-008 성공 응답의 data 필드 스키마"""
    jobId: UUID = Field(description="cleanup된 분석 작업 고유 ID")
    cleanedPath: str = Field(description="삭제된 임시 디렉토리 경로")
    cleanedAt: datetime = Field(description="cleanup 완료 시각")


class WorkspaceCleanupResponse(BaseModel):
    """
    DELETE /api/repo/analysis/{job_id}/workspace 성공 응답 스키마 (200 OK)
    """
    code: int = Field(default=200, description="HTTP 상태 코드")
    message: str = Field(default="success", description="응답 메시지")
    data: WorkspaceCleanupData



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
    model: str = Field(default="auto", description="적용된 분석 모델 정책")


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
            " IN_PROGRESS / CLONED / COMPLETED / FAILED"
        )
    )
    repoUrl: str = Field(description="분석 저장소 URL")
    stage: Optional[str] = Field(default=None, description="현재 분석 단계")
    progress: int = Field(default=0, ge=0, le=100, description="전체 진행률")
    statusMessage: Optional[str] = Field(default=None, description="현재 상태 설명")
    model: str = Field(default="auto", description="분석 모델 정책")
    report: Optional[dict[str, JsonValue]] = Field(default=None, description="완료된 구조 분석 리포트")
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
# API-FILE: 파일 컨텐츠 조회 응답 DTO
# ──────────────────────────────────────────────
class FileContentData(BaseModel):
    """GET /api/repo/analysis/{job_id}/files/content 성공 응답의 data 필드 스키마"""
    path: str = Field(description="저장소 내 상대 경로")
    content: str = Field(description="파일 텍스트 내용")
    language: Optional[str] = Field(default=None, description="감지된 언어")
    lines: int = Field(description="총 줄 수")
    truncated: bool = Field(
        default=False,
        description="파일 크기 초과로 내용이 잘렸는지 여부",
    )


class FileContentResponse(BaseModel):
    """
    GET /api/repo/analysis/{job_id}/files/content 성공 응답 스키마 (200 OK)
    """
    code: int = Field(default=200, description="HTTP 상태 코드")
    message: str = Field(default="success", description="응답 메시지")
    data: FileContentData


