{%- if cookiecutter.use_jwt %}
{%- if cookiecutter.use_postgresql and cookiecutter.use_sqlmodel %}
"""ConversationShare model — sharing conversations between users (SQLModel + PostgreSQL)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, SQLModel


class ConversationShare(SQLModel, table=True):
    """Share record granting a user access to another user's conversation.

    Attributes:
        id: Unique share identifier.
        conversation_id: The conversation being shared.
        shared_by: User who created the share (must be conversation owner).
        shared_with: User who receives access. NULL for link-only sharing.
        share_token: UUID4 token for public link access. NULL for direct sharing.
        permission: Access level — "view" (read-only) or "edit" (can add messages).
        created_at: When the share was created.
    """

    __tablename__ = "conversation_shares"
    __table_args__ = (
        UniqueConstraint("conversation_id", "shared_with", name="uq_share_conv_user"),
    )

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    conversation_id: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    shared_by: uuid.UUID = Field(
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    shared_with: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            PG_UUID(as_uuid=True),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
    )
    share_token: str | None = Field(default=None, max_length=64)
    permission: str = Field(default="view", max_length=10)  # view | edit
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime(timezone=True), nullable=False),
    )

    def __repr__(self) -> str:
        return f"<ConversationShare(id={self.id}, conv={self.conversation_id}, with={self.shared_with})>"


{%- elif cookiecutter.use_postgresql %}
"""ConversationShare model — sharing conversations between users (PostgreSQL async)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class ConversationShare(Base):
    """Share record granting a user access to another user's conversation."""

    __tablename__ = "conversation_shares"
    __table_args__ = (
        UniqueConstraint("conversation_id", "shared_with", name="uq_share_conv_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shared_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    shared_with: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    share_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    permission: Mapped[str] = mapped_column(
        String(10), nullable=False, default="view"
    )  # view | edit
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<ConversationShare(id={self.id}, conv={self.conversation_id}, with={self.shared_with})>"


{%- elif cookiecutter.use_sqlite and cookiecutter.use_sqlmodel %}
"""ConversationShare model — sharing conversations between users (SQLite + SQLModel)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, String, UniqueConstraint
from sqlmodel import Field, SQLModel


class ConversationShare(SQLModel, table=True):
    """Share record granting a user access to another user's conversation."""

    __tablename__ = "conversation_shares"
    __table_args__ = (
        UniqueConstraint("conversation_id", "shared_with", name="uq_share_conv_user"),
    )

    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        sa_column=Column(String(36), primary_key=True),
    )
    conversation_id: str = Field(
        sa_column=Column(
            String(36),
            ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
    )
    shared_by: str = Field(
        sa_column=Column(
            String(36),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
    )
    shared_with: str | None = Field(
        default=None,
        sa_column=Column(
            String(36),
            ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
    )
    share_token: str | None = Field(default=None, max_length=64)
    permission: str = Field(default="view", max_length=10)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        sa_column=Column(DateTime, nullable=False),
    )

    def __repr__(self) -> str:
        return f"<ConversationShare(id={self.id}, conv={self.conversation_id}, with={self.shared_with})>"


{%- elif cookiecutter.use_sqlite %}
"""ConversationShare model — sharing conversations between users (SQLite sync)."""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db.base import Base


class ConversationShare(Base):
    """Share record granting a user access to another user's conversation."""

    __tablename__ = "conversation_shares"
    __table_args__ = (
        UniqueConstraint("conversation_id", "shared_with", name="uq_share_conv_user"),
    )

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    conversation_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shared_by: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    shared_with: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    share_token: Mapped[str | None] = mapped_column(String(64), nullable=True, unique=True)
    permission: Mapped[str] = mapped_column(
        String(10), nullable=False, default="view"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<ConversationShare(id={self.id}, conv={self.conversation_id}, with={self.shared_with})>"


{%- elif cookiecutter.use_mongodb %}
"""ConversationShare document model — sharing conversations between users (MongoDB)."""

from datetime import UTC, datetime
from typing import Literal, Optional

from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, IndexModel


class ConversationShare(Document):
    """Share record granting a user access to another user's conversation."""

    conversation_id: str
    shared_by: str
    shared_with: Optional[str] = None
    share_token: Optional[str] = None
    permission: Literal["view", "edit"] = "view"
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "conversation_shares"
        indexes = [
            "conversation_id",
            "shared_with",
            "share_token",
            IndexModel(
                [("conversation_id", ASCENDING), ("shared_with", ASCENDING)],
                unique=True,
                partialFilterExpression={"shared_with": {"$ne": None}},
            ),
        ]

    def __repr__(self) -> str:
        return f"<ConversationShare(id={self.id}, conv={self.conversation_id}, with={self.shared_with})>"


{%- else %}
"""ConversationShare model — no supported database configured."""
{%- endif %}
{%- else %}
"""ConversationShare model — requires JWT authentication (use_jwt)."""
{%- endif %}
