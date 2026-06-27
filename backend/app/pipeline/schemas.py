"""
분석 파이프라인 관련 DTO 및 Enum 스키마 정의
"""

from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Enum 정의: 작업 상태
# ──────────────────────────────────────────────
class JobStatus(str, Enum):
    """분석 작업의 상태를 정의하는 열거형"""
    IN_PROGRESS = "IN_PROGRESS"
    CLONED = "CLONED"        # clone 완료, 파이프라인 미시작
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
# API-005 & API-006: SSE/WebSocket 이벤트 DTO
# ──────────────────────────────────────────────
class ProgressEvent(BaseModel):
    """
    SSE 및 WebSocket으로 전송되는 진행 상태 이벤트 스키마

    각 파이프라인 단계 전환 시마다 클라이언트에 push되는 데이터 구조.
    """
    stage: PipelineStage = Field(
        description="현재 단계 (CLONE / CODE_MAP / DOC_GEN / ONBOARDING / REPORT)"
    )
    status: JobStatus = Field(
        description="단계 상태 (IN_PROGRESS / COMPLETED / FAILED)"
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
