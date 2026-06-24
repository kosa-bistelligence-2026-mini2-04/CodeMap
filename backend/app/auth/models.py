"""
AUTH 도메인 SQLAlchemy ORM 모델 (PROJECT-AUTH)

users 테이블: 사용자 계정 (이메일 + bcrypt 해싱 비밀번호)
refresh_tokens 테이블: Refresh Token 저장 (Rotation 전략)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infra.database import Base


# ──────────────────────────────────────────────
# users 테이블
# ──────────────────────────────────────────────
class User(Base):
    """
    사용자 계정 엔티티

    이메일 + bcrypt 해싱 비밀번호로 인증.
    """

    __tablename__ = "users"

    __table_args__ = (
        Index("uq_users_email", "email", unique=True),
    )

    # 사용자 고유 ID (UUID)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # 이메일 (로그인 ID로 사용, 유니크)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    # bcrypt 해싱된 비밀번호
    hashed_password: Mapped[str] = mapped_column(Text, nullable=False)

    # 계정 생성 시각
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # 마지막 수정 시각
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


# ──────────────────────────────────────────────
# refresh_tokens 테이블
# ──────────────────────────────────────────────
class RefreshToken(Base):
    """
    Refresh Token 엔티티

    로그인 시 발급. Rotation 전략으로 사용 시마다 교체.
    logout 시 삭제하여 무효화.
    """

    __tablename__ = "refresh_tokens"

    # Refresh Token 고유 ID
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # 토큰 소유자 (users.id FK)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Refresh Token 원문 (jose JWT string)
    token: Mapped[str] = mapped_column(Text, nullable=False, unique=True)

    # 만료 시각
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # 발급 시각
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
