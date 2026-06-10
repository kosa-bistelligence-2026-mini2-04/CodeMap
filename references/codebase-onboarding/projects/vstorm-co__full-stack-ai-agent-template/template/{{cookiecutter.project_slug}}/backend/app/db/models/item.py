{%- if cookiecutter.include_example_crud and (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}
"""Item model — example resource scaffold.

This is a reference for adding new domains to the project. It demonstrates
the standard layered pattern (model → repo → service → route) without any
domain-specific complexity. Replace `Item` with your actual resource name
or copy/rename for each new domain.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
{%- if cookiecutter.use_postgresql %}
from sqlalchemy.dialects.postgresql import UUID
{%- endif %}
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Item(Base, TimestampMixin):
    """Owned resource — every Item belongs to one User."""

    __tablename__ = "items"

{%- if cookiecutter.use_postgresql %}
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
{%- else %}
    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
{%- endif %}
{%- if cookiecutter.use_postgresql %}
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
{%- else %}
    owner_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
{%- endif %}
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Relationships — uncomment if you want bidirectional access from User.
    # owner: Mapped["User"] = relationship("User", back_populates="items")

    def __repr__(self) -> str:
        return f"<Item(id={self.id}, name={self.name!r})>"
{%- endif %}
