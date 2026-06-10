{%- if cookiecutter.include_example_crud and (cookiecutter.use_postgresql or cookiecutter.use_sqlite) %}
"""Item repository — example resource scaffold.

Pure data-access functions. Always `db.flush()` + `db.refresh()`, never
`db.commit()` — the session auto-commits in `get_db_session`.
"""

from typing import Any
{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}

from sqlalchemy import func, select
{%- if cookiecutter.use_postgresql %}
from sqlalchemy.ext.asyncio import AsyncSession
{%- else %}
from sqlalchemy.orm import Session
{%- endif %}

from app.db.models.item import Item


{%- if cookiecutter.use_postgresql %}


async def get_by_id(db: AsyncSession, item_id: UUID) -> Item | None:
    result = await db.execute(select(Item).where(Item.id == item_id))
    return result.scalar_one_or_none()


async def list_for_owner(
    db: AsyncSession,
    *,
    owner_id: UUID,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Item], int]:
    base = select(Item).where(Item.owner_id == owner_id)
    total = (await db.execute(select(func.count()).select_from(base.subquery()))).scalar_one()
    rows = (
        await db.execute(
            base.order_by(Item.created_at.desc()).offset(skip).limit(limit)
        )
    ).scalars().all()
    return list(rows), int(total)


async def create(
    db: AsyncSession,
    *,
    owner_id: UUID,
    name: str,
    description: str | None = None,
    is_published: bool = False,
) -> Item:
    item = Item(
        owner_id=owner_id,
        name=name,
        description=description,
        is_published=is_published,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


async def update(
    db: AsyncSession,
    *,
    db_item: Item,
    update_data: dict[str, Any],
) -> Item:
    for field, value in update_data.items():
        setattr(db_item, field, value)
    await db.flush()
    await db.refresh(db_item)
    return db_item


async def delete(db: AsyncSession, item_id: UUID) -> Item | None:
    item = await get_by_id(db, item_id)
    if item:
        await db.delete(item)
        await db.flush()
    return item
{%- else %}


def get_by_id(db: Session, item_id: str) -> Item | None:
    return db.execute(select(Item).where(Item.id == item_id)).scalar_one_or_none()


def list_for_owner(
    db: Session,
    *,
    owner_id: str,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Item], int]:
    base = select(Item).where(Item.owner_id == owner_id)
    total = db.execute(select(func.count()).select_from(base.subquery())).scalar_one()
    rows = (
        db.execute(base.order_by(Item.created_at.desc()).offset(skip).limit(limit))
        .scalars()
        .all()
    )
    return list(rows), int(total)


def create(
    db: Session,
    *,
    owner_id: str,
    name: str,
    description: str | None = None,
    is_published: bool = False,
) -> Item:
    item = Item(
        owner_id=owner_id,
        name=name,
        description=description,
        is_published=is_published,
    )
    db.add(item)
    db.flush()
    db.refresh(item)
    return item


def update(db: Session, *, db_item: Item, update_data: dict[str, Any]) -> Item:
    for field, value in update_data.items():
        setattr(db_item, field, value)
    db.flush()
    db.refresh(db_item)
    return db_item


def delete(db: Session, item_id: str) -> Item | None:
    item = get_by_id(db, item_id)
    if item:
        db.delete(item)
        db.flush()
    return item
{%- endif %}
{%- endif %}
