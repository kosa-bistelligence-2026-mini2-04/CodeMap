{%- if cookiecutter.enable_billing and cookiecutter.enable_credits_system %}
"""CreditTransaction repository."""

{%- if cookiecutter.use_postgresql %}
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.db.models.credit_transaction import CreditTransaction, CreditTransactionType


async def create(
    db: AsyncSession,
    *,
    organization_id: uuid.UUID,
    delta: int,
    balance_after: int,
    type: CreditTransactionType,
    description: str,
    actor_user_id: uuid.UUID | None = None,
    stripe_reference: str | None = None,
    usage_event_id: uuid.UUID | None = None,
) -> CreditTransaction:
    tx = CreditTransaction(
        organization_id=organization_id,
        delta=delta,
        balance_after=balance_after,
        type=type,
        description=description,
        actor_user_id=actor_user_id,
        stripe_reference=stripe_reference,
        usage_event_id=usage_event_id,
    )
    db.add(tx)
    await db.flush()
    await db.refresh(tx)
    return tx


async def list_for_org(
    db: AsyncSession,
    organization_id: uuid.UUID,
    *,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[CreditTransaction], int]:
    count_q = select(func.count()).where(CreditTransaction.organization_id == organization_id)
    total = (await db.execute(count_q)).scalar_one()
    rows_q = (
        select(CreditTransaction)
        .where(CreditTransaction.organization_id == organization_id)
        .order_by(CreditTransaction.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(rows_q)
    return list(result.scalars().all()), total

{%- elif cookiecutter.use_sqlite %}
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.db.models.credit_transaction import CreditTransaction, CreditTransactionType


def create(
    db: Session,
    *,
    organization_id: str,
    delta: int,
    balance_after: int,
    type: CreditTransactionType,
    description: str,
    actor_user_id: str | None = None,
    stripe_reference: str | None = None,
    usage_event_id: str | None = None,
) -> CreditTransaction:
    tx = CreditTransaction(
        organization_id=organization_id,
        delta=delta,
        balance_after=balance_after,
        type=type,
        description=description,
        actor_user_id=actor_user_id,
        stripe_reference=stripe_reference,
        usage_event_id=usage_event_id,
    )
    db.add(tx)
    db.flush()
    db.refresh(tx)
    return tx


def list_for_org(
    db: Session,
    organization_id: str,
    *,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[CreditTransaction], int]:
    total = db.execute(
        select(func.count()).where(CreditTransaction.organization_id == organization_id)
    ).scalar_one()
    rows = list(
        db.execute(
            select(CreditTransaction)
            .where(CreditTransaction.organization_id == organization_id)
            .order_by(CreditTransaction.created_at.desc())
            .offset(skip)
            .limit(limit)
        ).scalars().all()
    )
    return rows, total

{%- elif cookiecutter.use_mongodb %}
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.db.models.credit_transaction import CreditTransaction, CreditTransactionType


async def create(
    db: AsyncIOMotorDatabase,
    *,
    organization_id: str,
    delta: int,
    balance_after: int,
    type: CreditTransactionType,
    description: str,
    actor_user_id: str | None = None,
    stripe_reference: str | None = None,
    usage_event_id: str | None = None,
) -> CreditTransaction:
    tx = CreditTransaction(
        organization_id=organization_id,
        delta=delta,
        balance_after=balance_after,
        type=type,
        description=description,
        actor_user_id=actor_user_id,
        stripe_reference=stripe_reference,
        usage_event_id=usage_event_id,
    )
    await tx.insert()
    return tx


async def list_for_org(
    db: AsyncIOMotorDatabase,
    organization_id: str,
    *,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[CreditTransaction], int]:
    query = CreditTransaction.find(CreditTransaction.organization_id == organization_id)
    total = await query.count()
    rows = await query.sort("-created_at").skip(skip).limit(limit).to_list()
    return rows, total

{%- endif %}
{%- else %}
"""CreditTransaction repository — not enabled."""
{%- endif %}
