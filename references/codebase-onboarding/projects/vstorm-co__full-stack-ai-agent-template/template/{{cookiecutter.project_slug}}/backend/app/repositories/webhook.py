{%- if cookiecutter.enable_webhooks and cookiecutter.use_database %}
{%- if cookiecutter.use_postgresql %}
"""Webhook repository (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.webhook import Webhook, WebhookDelivery
from app.schemas.webhook import WebhookUpdate


async def get_by_id(db: AsyncSession, webhook_id: UUID) -> Webhook | None:
    """Get webhook by ID."""
    return await db.get(Webhook, webhook_id)


async def get_list(
    db: AsyncSession,
    *,
    user_id: UUID | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Webhook], int]:
    """Get list of webhooks with pagination."""
    query = select(Webhook)
    if user_id:
        query = query.where(Webhook.user_id == user_id)
    query = query.order_by(Webhook.created_at.desc())

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Get paginated results
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def get_by_event(db: AsyncSession, event_type: str) -> list[Webhook]:
    """Get all active webhooks subscribed to an event type."""
    result = await db.execute(
        select(Webhook).where(
            Webhook.is_active.is_(True),
            Webhook.events.contains([event_type]),
        )
    )
    return list(result.scalars().all())


async def create(
    db: AsyncSession,
    *,
    name: str,
    url: str,
    secret: str,
    events: list[str],
    description: str | None = None,
    user_id: UUID | None = None,
) -> Webhook:
    """Create a new webhook."""
    webhook = Webhook(
        name=name,
        url=url,
        secret=secret,
        events=events,
        description=description,
{%- if cookiecutter.use_jwt %}
        user_id=user_id,
{%- endif %}
    )
    db.add(webhook)
    await db.flush()
    await db.refresh(webhook)
    return webhook


async def update(
    db: AsyncSession,
    webhook: Webhook,
    data: WebhookUpdate,
) -> Webhook:
    """Update a webhook."""
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(webhook, field, value)
    db.add(webhook)
    await db.flush()
    await db.refresh(webhook)
    return webhook


async def update_secret(db: AsyncSession, webhook: Webhook, new_secret: str) -> Webhook:
    """Update webhook secret."""
    webhook.secret = new_secret
    db.add(webhook)
    await db.flush()
    await db.refresh(webhook)
    return webhook


async def delete(db: AsyncSession, webhook: Webhook) -> None:
    """Delete a webhook."""
    await db.delete(webhook)
    await db.flush()


async def get_deliveries(
    db: AsyncSession,
    webhook_id: UUID,
    *,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[WebhookDelivery], int]:
    """Get delivery history for a webhook."""
    query = (
        select(WebhookDelivery)
        .where(WebhookDelivery.webhook_id == webhook_id)
        .order_by(WebhookDelivery.created_at.desc())
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all()), total


async def create_delivery(
    db: AsyncSession,
    *,
    webhook_id: UUID,
    event_type: str,
    payload: str,
) -> WebhookDelivery:
    """Create a new webhook delivery attempt record."""
    delivery = WebhookDelivery(
        webhook_id=webhook_id,
        event_type=event_type,
        payload=payload,
    )
    db.add(delivery)
    await db.flush()
    return delivery


async def save_delivery(db: AsyncSession, delivery: WebhookDelivery) -> WebhookDelivery:
    """Persist mutations made to a delivery record."""
    await db.flush()
    return delivery


{%- elif cookiecutter.use_sqlite %}
"""Webhook repository (SQLite sync)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from app.db.models.webhook import Webhook, WebhookDelivery
from app.schemas.webhook import WebhookUpdate


def get_by_id(db: DBSession, webhook_id: str) -> Webhook | None:
    """Get webhook by ID."""
    return db.get(Webhook, webhook_id)


def get_list(
    db: DBSession,
    *,
    user_id: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Webhook], int]:
    """Get list of webhooks with pagination."""
    query = select(Webhook)
    if user_id:
        query = query.where(Webhook.user_id == user_id)
    query = query.order_by(Webhook.created_at.desc())

    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    query = query.offset(skip).limit(limit)
    result = db.execute(query)
    return list(result.scalars().all()), total


def get_by_event(db: DBSession, event_type: str) -> list[Webhook]:
    """Get all active webhooks subscribed to an event type."""
    # For SQLite, we need to check if event is in the JSON array
    result = db.execute(select(Webhook).where(Webhook.is_active.is_(True)))
    webhooks = result.scalars().all()
    return [w for w in webhooks if event_type in w.events]


def create(
    db: DBSession,
    *,
    name: str,
    url: str,
    secret: str,
    events: list[str],
    description: str | None = None,
    user_id: str | None = None,
) -> Webhook:
    """Create a new webhook."""
    webhook = Webhook(
        name=name,
        url=url,
        secret=secret,
        description=description,
{%- if cookiecutter.use_jwt %}
        user_id=user_id,
{%- endif %}
    )
    webhook.events = events  # Use the property setter
    db.add(webhook)
    db.flush()
    db.refresh(webhook)
    return webhook


def update(
    db: DBSession,
    webhook: Webhook,
    data: WebhookUpdate,
) -> Webhook:
    """Update a webhook."""
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "events":
            webhook.events = value  # Use property setter
        else:
            setattr(webhook, field, value)
    db.add(webhook)
    db.flush()
    db.refresh(webhook)
    return webhook


def update_secret(db: DBSession, webhook: Webhook, new_secret: str) -> Webhook:
    """Update webhook secret."""
    webhook.secret = new_secret
    db.add(webhook)
    db.flush()
    db.refresh(webhook)
    return webhook


def delete(db: DBSession, webhook: Webhook) -> None:
    """Delete a webhook."""
    db.delete(webhook)
    db.flush()


def get_deliveries(
    db: DBSession,
    webhook_id: str,
    *,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[WebhookDelivery], int]:
    """Get delivery history for a webhook."""
    query = (
        select(WebhookDelivery)
        .where(WebhookDelivery.webhook_id == webhook_id)
        .order_by(WebhookDelivery.created_at.desc())
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_query) or 0

    query = query.offset(skip).limit(limit)
    result = db.execute(query)
    return list(result.scalars().all()), total


def create_delivery(
    db: DBSession,
    *,
    webhook_id: str,
    event_type: str,
    payload: str,
) -> WebhookDelivery:
    """Create a new webhook delivery attempt record."""
    delivery = WebhookDelivery(
        webhook_id=webhook_id,
        event_type=event_type,
        payload=payload,
    )
    db.add(delivery)
    db.flush()
    return delivery


def save_delivery(db: DBSession, delivery: WebhookDelivery) -> WebhookDelivery:
    """Persist mutations made to a delivery record."""
    db.flush()
    return delivery


{%- elif cookiecutter.use_mongodb %}
"""Webhook repository (MongoDB)."""

from app.db.models.webhook import Webhook, WebhookDelivery
from app.schemas.webhook import WebhookUpdate


async def get_by_id(webhook_id: str) -> Webhook | None:
    """Get webhook by ID."""
    return await Webhook.get(webhook_id)


async def get_list(
    *,
    user_id: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[Webhook], int]:
    """Get list of webhooks with pagination."""
    query = Webhook.find()
    if user_id:
        query = query.find(Webhook.user_id == user_id)

    total = await query.count()
    webhooks = await query.sort(-Webhook.created_at).skip(skip).limit(limit).to_list()
    return webhooks, total


async def get_by_event(event_type: str) -> list[Webhook]:
    """Get all active webhooks subscribed to an event type."""
    return await Webhook.find(
        Webhook.is_active == True,
        Webhook.events == event_type,  # MongoDB $elemMatch
    ).to_list()


async def create(
    *,
    name: str,
    url: str,
    secret: str,
    events: list[str],
    description: str | None = None,
    user_id: str | None = None,
) -> Webhook:
    """Create a new webhook."""
    webhook = Webhook(
        name=name,
        url=url,
        secret=secret,
        events=events,
        description=description,
{%- if cookiecutter.use_jwt %}
        user_id=user_id,
{%- endif %}
    )
    await webhook.insert()
    return webhook


async def update(
    webhook: Webhook,
    data: WebhookUpdate,
) -> Webhook:
    """Update a webhook."""
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(webhook, field, value)
    await webhook.save()
    return webhook


async def update_secret(webhook: Webhook, new_secret: str) -> Webhook:
    """Update webhook secret."""
    webhook.secret = new_secret
    await webhook.save()
    return webhook


async def delete(webhook: Webhook) -> None:
    """Delete a webhook."""
    await webhook.delete()


async def get_deliveries(
    webhook_id: str,
    *,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[WebhookDelivery], int]:
    """Get delivery history for a webhook."""
    query = WebhookDelivery.find(WebhookDelivery.webhook_id == webhook_id)
    total = await query.count()
    deliveries = await query.sort(-WebhookDelivery.created_at).skip(skip).limit(limit).to_list()
    return deliveries, total


{%- endif %}
{%- else %}
"""Webhook repository - not configured."""
{%- endif %}
