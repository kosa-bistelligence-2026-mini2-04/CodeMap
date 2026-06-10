{%- if cookiecutter.enable_billing %}
"""Plan and Price models — local mirror of Stripe Products/Prices."""

import uuid
{%- if cookiecutter.use_postgresql or cookiecutter.use_sqlite %}
from datetime import UTC, datetime

{%- if cookiecutter.use_postgresql and cookiecutter.use_sqlmodel %}
from sqlalchemy import Column, String, Text, Boolean, Integer, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlmodel import Field, Relationship, SQLModel
from app.db.base import TimestampMixin


class Plan(TimestampMixin, SQLModel, table=True):
    """Local mirror of a Stripe Product. Source of truth = Stripe Dashboard."""

    __tablename__ = "plan"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    code: str = Field(sa_column=Column(String(32), unique=True, nullable=False))
    display_name: str = Field(sa_column=Column(String(64), nullable=False))
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    is_active: bool = Field(default=True, sa_column=Column(Boolean, default=True, nullable=False))
    sort_order: int = Field(default=0, sa_column=Column(Integer, default=0, nullable=False))
    features: dict = Field(default_factory=dict, sa_column=Column(JSONB, default=dict, nullable=False))
    base_amount_cents: int = Field(default=0, sa_column=Column(Integer, default=0, nullable=False))
    included_seats: int = Field(default=1, sa_column=Column(Integer, default=1, nullable=False))
    extra_seat_amount_cents: int = Field(default=0, sa_column=Column(Integer, default=0, nullable=False))
    seats_min: int = Field(default=1, sa_column=Column(Integer, default=1, nullable=False))
    seats_max: int | None = Field(default=None, sa_column=Column(Integer, nullable=True))
    monthly_credits_base: int = Field(default=0, sa_column=Column(Integer, default=0, nullable=False))
    monthly_credits_per_seat: int = Field(default=0, sa_column=Column(Integer, default=0, nullable=False))

    prices: list["Price"] = Relationship(
        back_populates="plan",
        sa_relationship_kwargs={"cascade": "all, delete-orphan"},
    )

    def __repr__(self) -> str:
        return f"<Plan(code={self.code}, name={self.display_name})>"


class Price(TimestampMixin, SQLModel, table=True):
    """Local mirror of a Stripe Price. Source of truth = Stripe Dashboard."""

    __tablename__ = "price"

    id: uuid.UUID = Field(
        default_factory=uuid.uuid4,
        sa_column=Column(PG_UUID(as_uuid=True), primary_key=True),
    )
    plan_id: uuid.UUID = Field(
        sa_column=Column(PG_UUID(as_uuid=True), ForeignKey("plan.id", ondelete="CASCADE"), nullable=False, index=True)
    )
    stripe_price_id: str = Field(sa_column=Column(String(64), unique=True, index=True, nullable=False))
    interval: str = Field(sa_column=Column(String(16), nullable=False))  # month, year, one_time
    amount_cents: int = Field(default=0, sa_column=Column(Integer, default=0, nullable=False))
    currency: str = Field(default="{{ cookiecutter.billing_default_currency }}", sa_column=Column(String(3), nullable=False))
    trial_period_days: int | None = Field(default=None, sa_column=Column(Integer, nullable=True))
    is_active: bool = Field(default=True, sa_column=Column(Boolean, default=True, nullable=False))
    billing_scheme: str = Field(default="per_unit", sa_column=Column(String(16), nullable=False))
    tiers_mode: str | None = Field(default=None, sa_column=Column(String(16), nullable=True))
    tiers: list | None = Field(default=None, sa_column=Column(JSONB, nullable=True))
    credits_grant: int | None = Field(default=None, sa_column=Column(Integer, nullable=True))

    plan: Plan = Relationship(back_populates="prices")

    def __repr__(self) -> str:
        return f"<Price(stripe_price_id={self.stripe_price_id}, interval={self.interval})>"


{%- elif cookiecutter.use_postgresql and cookiecutter.use_sqlalchemy %}
from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class Plan(Base, TimestampMixin):
    __tablename__ = "plan"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    features: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    base_amount_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    included_seats: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    extra_seat_amount_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    seats_min: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    seats_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_credits_base: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    monthly_credits_per_seat: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    prices: Mapped[list["Price"]] = relationship("Price", back_populates="plan", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Plan(code={self.code}, name={self.display_name})>"


class Price(Base, TimestampMixin):
    __tablename__ = "price"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("plan.id", ondelete="CASCADE"), index=True, nullable=False)
    stripe_price_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    interval: Mapped[str] = mapped_column(String(16), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="{{ cookiecutter.billing_default_currency }}")
    trial_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    billing_scheme: Mapped[str] = mapped_column(String(16), default="per_unit", nullable=False)
    tiers_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    tiers: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    credits_grant: Mapped[int | None] = mapped_column(Integer, nullable=True)

    plan: Mapped[Plan] = relationship("Plan", back_populates="prices")

    def __repr__(self) -> str:
        return f"<Price(stripe_price_id={self.stripe_price_id}, interval={self.interval})>"


{%- elif cookiecutter.use_sqlite and cookiecutter.use_sqlmodel %}
import json
from sqlalchemy import Column, String, Text, Boolean, Integer
from sqlmodel import Field, Relationship, SQLModel
from app.db.base import TimestampMixin


class Plan(TimestampMixin, SQLModel, table=True):
    __tablename__ = "plan"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    code: str = Field(sa_column=Column(String(32), unique=True, nullable=False))
    display_name: str = Field(sa_column=Column(String(64), nullable=False))
    description: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    is_active: bool = Field(default=True)
    sort_order: int = Field(default=0)
    _features: str = Field(default="{}", sa_column=Column("features", Text, nullable=False))
    base_amount_cents: int = Field(default=0)
    included_seats: int = Field(default=1)
    extra_seat_amount_cents: int = Field(default=0)
    seats_min: int = Field(default=1)
    seats_max: int | None = Field(default=None)
    monthly_credits_base: int = Field(default=0)
    monthly_credits_per_seat: int = Field(default=0)

    prices: list["Price"] = Relationship(back_populates="plan", sa_relationship_kwargs={"cascade": "all, delete-orphan"})

    @property
    def features(self) -> dict:
        return json.loads(self._features)

    @features.setter
    def features(self, value: dict) -> None:
        self._features = json.dumps(value)

    def __repr__(self) -> str:
        return f"<Plan(code={self.code})>"


class Price(TimestampMixin, SQLModel, table=True):
    __tablename__ = "price"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    plan_id: str = Field(foreign_key="plan.id", index=True)
    stripe_price_id: str = Field(sa_column=Column(String(64), unique=True, index=True, nullable=False))
    interval: str = Field(sa_column=Column(String(16), nullable=False))
    amount_cents: int = Field(default=0)
    currency: str = Field(default="{{ cookiecutter.billing_default_currency }}")
    trial_period_days: int | None = Field(default=None)
    is_active: bool = Field(default=True)
    billing_scheme: str = Field(default="per_unit")
    tiers_mode: str | None = Field(default=None)
    credits_grant: int | None = Field(default=None)

    plan: Plan = Relationship(back_populates="prices")

    def __repr__(self) -> str:
        return f"<Price(stripe_price_id={self.stripe_price_id})>"


{%- elif cookiecutter.use_sqlite and cookiecutter.use_sqlalchemy %}
import json
from sqlalchemy import Column, String, Text, Boolean, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin


class Plan(Base, TimestampMixin):
    __tablename__ = "plan"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    _features: Mapped[str] = mapped_column("features", Text, nullable=False, default="{}")
    base_amount_cents: Mapped[int] = mapped_column(Integer, default=0)
    included_seats: Mapped[int] = mapped_column(Integer, default=1)
    extra_seat_amount_cents: Mapped[int] = mapped_column(Integer, default=0)
    seats_min: Mapped[int] = mapped_column(Integer, default=1)
    seats_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    monthly_credits_base: Mapped[int] = mapped_column(Integer, default=0)
    monthly_credits_per_seat: Mapped[int] = mapped_column(Integer, default=0)

    prices: Mapped[list["Price"]] = relationship("Price", back_populates="plan", cascade="all, delete-orphan")

    @property
    def features(self) -> dict:
        return json.loads(self._features)

    @features.setter
    def features(self, value: dict) -> None:
        self._features = json.dumps(value)

    def __repr__(self) -> str:
        return f"<Plan(code={self.code})>"


class Price(Base, TimestampMixin):
    __tablename__ = "price"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("plan.id", ondelete="CASCADE"), index=True, nullable=False)
    stripe_price_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    interval: Mapped[str] = mapped_column(String(16), nullable=False)
    amount_cents: Mapped[int] = mapped_column(Integer, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="{{ cookiecutter.billing_default_currency }}")
    trial_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    billing_scheme: Mapped[str] = mapped_column(String(16), default="per_unit")
    tiers_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)
    credits_grant: Mapped[int | None] = mapped_column(Integer, nullable=True)

    plan: Mapped[Plan] = relationship("Plan", back_populates="prices")

    def __repr__(self) -> str:
        return f"<Price(stripe_price_id={self.stripe_price_id})>"

{%- endif %}
{%- elif cookiecutter.use_mongodb %}
from datetime import datetime
from typing import Optional
from beanie import Document


class Plan(Document):
    code: str
    display_name: str
    description: Optional[str] = None
    is_active: bool = True
    sort_order: int = 0
    features: dict = {}
    base_amount_cents: int = 0
    included_seats: int = 1
    extra_seat_amount_cents: int = 0
    seats_min: int = 1
    seats_max: Optional[int] = None
    monthly_credits_base: int = 0
    monthly_credits_per_seat: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "plans"


class Price(Document):
    plan_id: str
    stripe_price_id: str
    interval: str
    amount_cents: int = 0
    currency: str = "{{ cookiecutter.billing_default_currency }}"
    trial_period_days: Optional[int] = None
    is_active: bool = True
    billing_scheme: str = "per_unit"
    tiers_mode: Optional[str] = None
    credits_grant: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    class Settings:
        name = "prices"

{%- endif %}
{%- else %}
"""Plan and Price models — not enabled (enable_billing=false)."""
{%- endif %}
