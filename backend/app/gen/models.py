"""
DOCS-GEN 도메인 데이터베이스 엔티티 모듈

DOCS_GEN_SPEC.md (B-301)에 따라 생성된 온보딩 가이드북 Markdown을
PostgreSQL docs 테이블에 저장하는 SQLAlchemy ORM 모델을 정의한다.

DB 테이블:
  docs — repo_id, job_id, doc_type, content, version, created_at
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.database import Base


# ──────────────────────────────────────────────
# OnboardingDoc — 온보딩 가이드북 저장 엔티티
# ──────────────────────────────────────────────
class OnboardingDoc(Base):
    '''
    생성된 온보딩 가이드북 Markdown 저장 엔티티 (DOCS-GEN-B-301)

    - 동일 repo_id의 최신 버전 조회를 위해 (repo_id, version) 복합 인덱스 사용
    - 버전 재생성 시 이전 버전은 유지하고 version 번호를 증가시킨다
    '''

    __tablename__ = "docs"

    __table_args__ = (
        UniqueConstraint("repo_id", "version", name="uq_docs_repo_version"),
        Index("idx_docs_repo_id", "repo_id"),
    )

    ## 문서 고유 ID
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    ## 저장소 ID (analysis_jobs.id 참조)
    repo_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("analysis_jobs.id", ondelete="CASCADE"),
        nullable=False,
        comment="대상 저장소 AnalysisJob ID",
    )

    ## 연결된 분석 작업 ID
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
        comment="문서 생성을 트리거한 분석 작업 ID",
    )

    ## 문서 유형 (기본: onboarding)
    doc_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="onboarding",
        comment="문서 유형 (onboarding / summary 등)",
    )

    ## Markdown 전문
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="생성된 Markdown 가이드북 전문",
    )

    ## 가이드북 버전 (재생성 시 증가)
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        comment="가이드북 버전 번호 (1부터 시작, 재생성 시 증가)",
    )

    ## 생성 시각
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
