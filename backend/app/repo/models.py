"""
분석 작업(AnalysisJob) 데이터베이스 엔티티 모듈

분석 작업의 상태, 저장소 메타데이터, 파이프라인 진행 상황 등을
PostgreSQL 테이블에 매핑하는 SQLAlchemy ORM 모델을 정의한다.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, String, Integer, Text, DateTime, Index, text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import JSONB, UUID

from app.infra.database import Base
from app.repo.schemas import JobStatus, PipelineStage


# ──────────────────────────────────────────────
# 분석 작업 테이블 엔티티 (analysis_jobs)
# ──────────────────────────────────────────────
class AnalysisJob(Base):
    """
    분석 작업 엔티티

    GitHub 저장소 분석 요청 시 생성되며,
    파이프라인 진행에 따라 status, stage, progress가 업데이트된다.
    """

    __tablename__ = "analysis_jobs"

    __table_args__ = (
        Index(
            "uq_analysis_jobs_in_progress",
            "repo_url",
            "branch",
            unique=True,
            postgresql_where=text("status = 'IN_PROGRESS'"),
        ),
    )

    # 분석 작업 고유 ID (UUID) - 자동생성
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # 사용자 고유 ID (인증/권한 검증용)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)

    # 팀 고유 ID (팀 워크스페이스 격리용)
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )

    # 개인(Private) 여부 (true면 본인만 접근 가능)
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # GitHub 저장소 전체 URL - https://github.com/owner/repo
    repo_url: Mapped[str] = mapped_column(Text, nullable=False)

    # 저장소 이름 (URL에서 파싱) - repo
    repo_name: Mapped[str] = mapped_column(String(255), nullable=False)

    # 저장소 소유자 (URL에서 파싱) - owner
    owner: Mapped[str] = mapped_column(String(255), nullable=False)

    # 분석 대상 브랜치 - main
    branch: Mapped[str] = mapped_column(String(255), nullable=False, default="main")

    # 현재 작업 상태 - (IN_PROGRESS / COMPLETED / FAILED)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=JobStatus.IN_PROGRESS.value
    )

    # 현재 파이프라인 단계 - (CLONE / CODE_MAP / DOC_GEN / ONBOARDING / REPORT)
    stage: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # 전체 진행률 - (0 ~ 100)
    progress: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # 진행 상태 메시지 - "저장소 복제 중..."
    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    model_used: Mapped[str] = mapped_column(String(255), nullable=False, default="auto")

    force_refresh: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    report_json: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    # 작업 생성 시각
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # 마지막 상태 변경(수정) 시각
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
