{%- if cookiecutter.enable_billing %}
"""StripeEvent repository — idempotency helpers."""

{%- if cookiecutter.use_postgresql %}
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.stripe_event import StripeEvent


async def get_by_stripe_id(db: AsyncSession, stripe_event_id: str) -> StripeEvent | None:
    result = await db.execute(select(StripeEvent).where(StripeEvent.stripe_event_id == stripe_event_id))
    return result.scalar_one_or_none()


async def create(db: AsyncSession, *, stripe_event_id: str, event_type: str, payload: dict) -> StripeEvent:
    event = StripeEvent(stripe_event_id=stripe_event_id, event_type=event_type, payload=payload)
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


async def mark_processed(db: AsyncSession, *, db_event: StripeEvent) -> StripeEvent:
    db_event.status = "processed"
    await db.flush()
    await db.refresh(db_event)
    return db_event


async def mark_failed(db: AsyncSession, *, db_event: StripeEvent, error: str) -> StripeEvent:
    db_event.status = "failed"
    db_event.error = error
    await db.flush()
    await db.refresh(db_event)
    return db_event

{%- elif cookiecutter.use_sqlite %}
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models.stripe_event import StripeEvent


def get_by_stripe_id(db: Session, stripe_event_id: str) -> StripeEvent | None:
    return db.execute(select(StripeEvent).where(StripeEvent.stripe_event_id == stripe_event_id)).scalar_one_or_none()


def create(db: Session, *, stripe_event_id: str, event_type: str, payload: dict) -> StripeEvent:
    event = StripeEvent(stripe_event_id=stripe_event_id, event_type=event_type, payload=payload)
    db.add(event)
    db.flush()
    db.refresh(event)
    return event


def mark_processed(db: Session, *, db_event: StripeEvent) -> StripeEvent:
    db_event.status = "processed"
    db.flush()
    db.refresh(db_event)
    return db_event


def mark_failed(db: Session, *, db_event: StripeEvent, error: str) -> StripeEvent:
    db_event.status = "failed"
    db_event.error = error
    db.flush()
    db.refresh(db_event)
    return db_event

{%- elif cookiecutter.use_mongodb %}
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.models.stripe_event import StripeEvent


async def get_by_stripe_id(db: AsyncIOMotorDatabase, stripe_event_id: str) -> StripeEvent | None:
    return await StripeEvent.find_one(StripeEvent.stripe_event_id == stripe_event_id)


async def create(db: AsyncIOMotorDatabase, *, stripe_event_id: str, event_type: str, payload: dict) -> StripeEvent:
    event = StripeEvent(stripe_event_id=stripe_event_id, event_type=event_type, payload=payload)
    await event.insert()
    return event


async def mark_processed(db: AsyncIOMotorDatabase, *, db_event: StripeEvent) -> StripeEvent:
    db_event.status = "processed"
    await db_event.save()
    return db_event


async def mark_failed(db: AsyncIOMotorDatabase, *, db_event: StripeEvent, error: str) -> StripeEvent:
    db_event.status = "failed"
    db_event.error = error
    await db_event.save()
    return db_event

{%- endif %}
{%- else %}
"""StripeEvent repository — not enabled (enable_billing=false)."""
{%- endif %}
