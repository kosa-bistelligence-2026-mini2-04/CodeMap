"""
AUTH 도메인 SQLAlchemy ORM 모델 (PROJECT-AUTH)

users 테이블: 사용자 계정 (이메일 + bcrypt 해싱 비밀번호)
refresh_tokens 테이블: Refresh Token 저장 (Rotation 전략)
"""

import uuid
from datetime import datetime, timedelta, timezone

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


# ──────────────────────────────────────────────
# teams 테이블
# ──────────────────────────────────────────────
class Team(Base):
    """
    팀 엔티티
    """
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


# ──────────────────────────────────────────────
# team_members 테이블
# ──────────────────────────────────────────────
class TeamMember(Base):
    """
    팀 멤버 매핑 테이블 (회원 <-> 팀)
    role: "owner", "member", "pending" 등
    """
    __tablename__ = "team_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="member")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="active")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )


# ──────────────────────────────────────────────
# team_invites 테이블 (PROJECT-TEAM-API-003~006)
# 생성 -> 수락/거절 -> 멤버십 활성화 흐름을 위한 초대 상태 저장
# ──────────────────────────────────────────────
class TeamInvite(Base):
    """
    팀 초대 엔티티

    status: pending, accepted, declined, expired, cancelled
    이메일 기준으로 초대하며, 수락 시 초대 이메일과 로그인 이메일이 일치해야 한다.
    """
    __tablename__ = "team_invites"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    team_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    invited_by_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False, default="member")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc) + timedelta(days=7),
    )
