{%- if cookiecutter.enable_billing %}
"""Plan and Price repository."""

{%- if cookiecutter.use_postgresql %}
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models.plan import Plan, Price


async def get_plan_by_code(db: AsyncSession, code: str) -> Plan | None:
    result = await db.execute(select(Plan).where(Plan.code == code, Plan.is_active))
    return result.scalar_one_or_none()


async def get_plan_by_id(db: AsyncSession, plan_id: uuid.UUID) -> Plan | None:
    return await db.get(Plan, plan_id)


async def list_active_plans(db: AsyncSession) -> list[Plan]:
    result = await db.execute(select(Plan).where(Plan.is_active).order_by(Plan.sort_order))
    return list(result.scalars().all())


async def get_price_by_id(db: AsyncSession, price_id: uuid.UUID) -> Price | None:
    return await db.get(Price, price_id)


async def get_price_by_stripe_id(db: AsyncSession, stripe_price_id: str) -> Price | None:
    result = await db.execute(select(Price).where(Price.stripe_price_id == stripe_price_id))
    return result.scalar_one_or_none()


async def upsert_plan(db: AsyncSession, *, code: str, display_name: str, **kwargs) -> Plan:
    existing = await get_plan_by_code(db, code)
    if existing:
        for k, v in kwargs.items():
            setattr(existing, k, v)
        existing.display_name = display_name
        await db.flush()
        await db.refresh(existing)
        return existing
    plan = Plan(code=code, display_name=display_name, **kwargs)
    db.add(plan)
    await db.flush()
    await db.refresh(plan)
    return plan


async def upsert_price(db: AsyncSession, *, stripe_price_id: str, plan_id: uuid.UUID, **kwargs) -> Price:
    existing = await get_price_by_stripe_id(db, stripe_price_id)
    if existing:
        for k, v in kwargs.items():
            setattr(existing, k, v)
        await db.flush()
        await db.refresh(existing)
        return existing
    price = Price(stripe_price_id=stripe_price_id, plan_id=plan_id, **kwargs)
    db.add(price)
    await db.flush()
    await db.refresh(price)
    return price

{%- elif cookiecutter.use_sqlite %}
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db.models.plan import Plan, Price


def get_plan_by_code(db: Session, code: str) -> Plan | None:
    return db.execute(select(Plan).where(Plan.code == code, Plan.is_active)).scalar_one_or_none()


def list_active_plans(db: Session) -> list[Plan]:
    return list(db.execute(select(Plan).where(Plan.is_active).order_by(Plan.sort_order)).scalars().all())


def get_price_by_id(db: Session, price_id: str) -> Price | None:
    return db.get(Price, price_id)


def get_price_by_stripe_id(db: Session, stripe_price_id: str) -> Price | None:
    return db.execute(select(Price).where(Price.stripe_price_id == stripe_price_id)).scalar_one_or_none()


def upsert_plan(db: Session, *, code: str, display_name: str, **kwargs) -> Plan:
    existing = get_plan_by_code(db, code)
    if existing:
        for k, v in kwargs.items():
            setattr(existing, k, v)
        existing.display_name = display_name
        db.flush()
        db.refresh(existing)
        return existing
    plan = Plan(code=code, display_name=display_name, **kwargs)
    db.add(plan)
    db.flush()
    db.refresh(plan)
    return plan


def upsert_price(db: Session, *, stripe_price_id: str, plan_id: str, **kwargs) -> Price:
    existing = get_price_by_stripe_id(db, stripe_price_id)
    if existing:
        for k, v in kwargs.items():
            setattr(existing, k, v)
        db.flush()
        db.refresh(existing)
        return existing
    price = Price(stripe_price_id=stripe_price_id, plan_id=plan_id, **kwargs)
    db.add(price)
    db.flush()
    db.refresh(price)
    return price

{%- elif cookiecutter.use_mongodb %}
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.models.plan import Plan, Price


async def list_active_plans(db: AsyncIOMotorDatabase) -> list[Plan]:
    return await Plan.find(Plan.is_active == True).sort("+sort_order").to_list()  # noqa: E712


async def get_plan_by_code(db: AsyncIOMotorDatabase, code: str) -> Plan | None:
    return await Plan.find_one(Plan.code == code)


async def get_price_by_stripe_id(db: AsyncIOMotorDatabase, stripe_price_id: str) -> Price | None:
    return await Price.find_one(Price.stripe_price_id == stripe_price_id)

{%- endif %}
{%- else %}
"""Plan repository — not enabled (enable_billing=false)."""
{%- endif %}
