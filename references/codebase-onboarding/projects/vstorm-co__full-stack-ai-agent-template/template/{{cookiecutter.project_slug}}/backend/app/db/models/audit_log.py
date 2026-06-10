{%- if cookiecutter.enable_teams %}
{%- if cookiecutter.use_postgresql and cookiecutter.use_sqlmodel %}
"""App admin audit log model (PostgreSQL/SQLModel)."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Column, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlmodel import Field, SQLModel

from app.db.base import TimestampMixin


class AppAdminAuditLog(TimestampMixin, SQLModel, table=True):
    """Records privileged actions performed by app admins or org owners."""

    __tablename__ = "app_admin_audit_logs"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    actor_user_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), nullable=False, index=True)
    )
    organization_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(PG_UUID(as_uuid=True), nullable=True, index=True),
    )
    action: str = Field(sa_column=Column(String(100), nullable=False, index=True))
    target_type: str | None = Field(default=None, sa_column=Column(String(100), nullable=True))
    target_id: str | None = Field(default=None, sa_column=Column(String(36), nullable=True))
    details: dict[str, Any] | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    ip_address: str | None = Field(default=None, sa_column=Column(String(45), nullable=True))

    def __repr__(self) -> str:
        return f"<AppAdminAuditLog(id={self.id}, action={self.action}, actor={self.actor_user_id})>"


{%- elif cookiecutter.use_postgresql %}
"""App admin audit log model (PostgreSQL/SQLAlchemy)."""

import uuid
from typing import Any

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AppAdminAuditLog(Base, TimestampMixin):
    """Records privileged actions performed by app admins or org owners."""

    __tablename__ = "app_admin_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    details: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    def __repr__(self) -> str:
        return f"<AppAdminAuditLog(id={self.id}, action={self.action}, actor={self.actor_user_id})>"


{%- elif cookiecutter.use_sqlite and cookiecutter.use_sqlmodel %}
"""App admin audit log model (SQLite/SQLModel)."""

import uuid
from typing import Any

from sqlalchemy import Column, String, Text
from sqlmodel import Field, SQLModel

from app.db.base import TimestampMixin


class AppAdminAuditLog(TimestampMixin, SQLModel, table=True):
    """Records privileged actions performed by app admins or org owners."""

    __tablename__ = "app_admin_audit_logs"

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True),
    )
    actor_user_id: str = Field(sa_column=Column(String(36), nullable=False, index=True))
    organization_id: str | None = Field(
        default=None, sa_column=Column(String(36), nullable=True, index=True)
    )
    action: str = Field(sa_column=Column(String(100), nullable=False, index=True))
    target_type: str | None = Field(default=None, sa_column=Column(String(100), nullable=True))
    target_id: str | None = Field(default=None, sa_column=Column(String(36), nullable=True))
    details: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    ip_address: str | None = Field(default=None, sa_column=Column(String(45), nullable=True))

    def __repr__(self) -> str:
        return f"<AppAdminAuditLog(id={self.id}, action={self.action}, actor={self.actor_user_id})>"


{%- elif cookiecutter.use_sqlite %}
"""App admin audit log model (SQLite/SQLAlchemy)."""

import uuid

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class AppAdminAuditLog(Base, TimestampMixin):
    """Records privileged actions performed by app admins or org owners."""

    __tablename__ = "app_admin_audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    actor_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    organization_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)

    def __repr__(self) -> str:
        return f"<AppAdminAuditLog(id={self.id}, action={self.action}, actor={self.actor_user_id})>"


{%- elif cookiecutter.use_mongodb %}
"""App admin audit log document model (MongoDB)."""

from datetime import UTC, datetime
from typing import Any, Optional

from beanie import Document
from pydantic import Field


class AppAdminAuditLog(Document):
    """Records privileged actions performed by app admins or org owners."""

    actor_user_id: str
    organization_id: Optional[str] = None
    action: str
    target_type: Optional[str] = None
    target_id: Optional[str] = None
    details: Optional[dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "app_admin_audit_logs"
        indexes = ["actor_user_id", "organization_id", "action"]


{%- else %}
"""Audit log — not configured."""
{%- endif %}
{%- else %}
"""Audit log — not configured (enable_teams=false)."""
{%- endif %}
