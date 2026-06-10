{%- if cookiecutter.enable_billing %}
"""Subscription model — local mirror of Stripe Subscription."""

import enum
import uuid
{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite %}
from datetime import UTC, datetime

{%- if cookiecutter.use_postgresql and cookiecutter.use_sqlmodel %}
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlmodel import Field, Relationship, SQLModel
from app.db.base import TimestampMixin


class SubscriptionStatus(enum.StrEnum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    PAUSED = "paused"


class Subscription(TimestampMixin, SQLModel, table=True):
    __tablename__ = "subscription"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, sa_column=Column(PG_UUID(as_uuid=True), primary_key=True))
    organization_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, index=True, nullable=False)
    )
    stripe_subscription_id: str = Field(sa_column=Column(String(64), unique=True, index=True, nullable=False))
    stripe_customer_id: str = Field(sa_column=Column(String(64), index=True, nullable=False))
    stripe_item_id: str = Field(sa_column=Column(String(64), nullable=False))
    price_id: uuid.UUID = Field(sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("price.id"), nullable=False))
    seats_quantity: int = Field(default=1, sa_column=Column(Integer, default=1, nullable=False))
    status: SubscriptionStatus = Field(sa_column=Column(SQLEnum(SubscriptionStatus), index=True, nullable=False))
    current_period_start: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    current_period_end: datetime = Field(sa_column=Column(DateTime(timezone=True), nullable=False))
    cancel_at_period_end: bool = Field(default=False)
    canceled_at: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    trial_start: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))
    trial_end: datetime | None = Field(default=None, sa_column=Column(DateTime(timezone=True), nullable=True))

    def __repr__(self) -> str:
        return f"<Subscription(stripe_id={self.stripe_subscription_id}, status={self.status})>"


{%- elif cookiecutter.use_postgresql and cookiecutter.use_sqlalchemy %}
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class SubscriptionStatus(enum.StrEnum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    PAUSED = "paused"


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscription"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    organization_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, index=True)
    stripe_subscription_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    stripe_customer_id: Mapped[str] = mapped_column(String(64), index=True)
    stripe_item_id: Mapped[str] = mapped_column(String(64))
    price_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("price.id"))
    seats_quantity: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[SubscriptionStatus] = mapped_column(SQLEnum(SubscriptionStatus), index=True)
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trial_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<Subscription(stripe_id={self.stripe_subscription_id}, status={self.status})>"


{%- elif cookiecutter.use_sqlite %}
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Enum as SQLEnum, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, TimestampMixin


class SubscriptionStatus(enum.StrEnum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    PAUSED = "paused"


class Subscription(Base, TimestampMixin):
    __tablename__ = "subscription"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), unique=True, index=True)
    stripe_subscription_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    stripe_customer_id: Mapped[str] = mapped_column(String(64), index=True)
    stripe_item_id: Mapped[str] = mapped_column(String(64))
    price_id: Mapped[str] = mapped_column(String(36), ForeignKey("price.id"))
    seats_quantity: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(32), index=True)
    current_period_start: Mapped[datetime] = mapped_column(DateTime)
    current_period_end: Mapped[datetime] = mapped_column(DateTime)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    trial_start: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    trial_end: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    def __repr__(self) -> str:
        return f"<Subscription(stripe_id={self.stripe_subscription_id}, status={self.status})>"

{%- endif %}
{%- elif cookiecutter.use_mongodb %}
import enum
from datetime import datetime
from typing import Optional
from beanie import Document


class SubscriptionStatus(enum.StrEnum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"


class Subscription(Document):
    organization_id: str
    stripe_subscription_id: str
    stripe_customer_id: str
    stripe_item_id: str
    price_id: str
    seats_quantity: int = 1
    status: SubscriptionStatus
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool = False
    canceled_at: Optional[datetime] = None
    trial_start: Optional[datetime] = None
    trial_end: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "subscriptions"

{%- endif %}
{%- else %}
"""Subscription model — not enabled (enable_billing=false)."""
{%- endif %}
