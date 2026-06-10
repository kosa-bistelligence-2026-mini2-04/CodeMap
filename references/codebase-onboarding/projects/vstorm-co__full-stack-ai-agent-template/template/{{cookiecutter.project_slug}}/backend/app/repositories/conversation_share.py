{%- if cookiecutter.use_jwt %}
{%- if cookiecutter.use_postgresql %}
"""ConversationShare repository (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.conversation import Conversation
from app.db.models.conversation_share import ConversationShare


async def get_by_id(db: AsyncSession, share_id: UUID) -> ConversationShare | None:
    """Get a share by ID."""
    return await db.get(ConversationShare, share_id)


async def get_share(
    db: AsyncSession, conversation_id: UUID, shared_with: UUID
) -> ConversationShare | None:
    """Get a share by conversation + user composite key."""
    result = await db.execute(
        select(ConversationShare).where(
            ConversationShare.conversation_id == conversation_id,
            ConversationShare.shared_with == shared_with,
        )
    )
    return result.scalar_one_or_none()


async def get_by_token(db: AsyncSession, token: str) -> ConversationShare | None:
    """Get a share by its public token."""
    result = await db.execute(
        select(ConversationShare).where(ConversationShare.share_token == token)
    )
    return result.scalar_one_or_none()


async def get_shares_for_conversation(
    db: AsyncSession, conversation_id: UUID
) -> list[ConversationShare]:
    """List all shares for a conversation."""
    result = await db.execute(
        select(ConversationShare)
        .where(ConversationShare.conversation_id == conversation_id)
        .order_by(ConversationShare.created_at.desc())
    )
    return list(result.scalars().all())


async def get_conversations_shared_with_user(
    db: AsyncSession, user_id: UUID, *, skip: int = 0, limit: int = 50
) -> list[Conversation]:
    """Get conversations shared with a specific user."""
    result = await db.execute(
        select(Conversation)
        .join(ConversationShare, ConversationShare.conversation_id == Conversation.id)
        .where(ConversationShare.shared_with == user_id)
        .order_by(Conversation.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


async def count_conversations_shared_with_user(
    db: AsyncSession, user_id: UUID
) -> int:
    """Count conversations shared with a specific user."""
    result = await db.scalar(
        select(func.count())
        .select_from(ConversationShare)
        .where(ConversationShare.shared_with == user_id)
    )
    return result or 0


async def user_has_access(
    db: AsyncSession, conversation_id: UUID, user_id: UUID
) -> ConversationShare | None:
    """Check if user has any share access to a conversation."""
    return await get_share(db, conversation_id, user_id)


async def create(
    db: AsyncSession,
    *,
    conversation_id: UUID,
    shared_by: UUID,
    shared_with: UUID | None = None,
    share_token: str | None = None,
    permission: str = "view",
) -> ConversationShare:
    """Create a new conversation share."""
    share = ConversationShare(
        conversation_id=conversation_id,
        shared_by=shared_by,
        shared_with=shared_with,
        share_token=share_token,
        permission=permission,
    )
    db.add(share)
    await db.flush()
    await db.refresh(share)
    return share


async def update(
    db: AsyncSession,
    *,
    db_share: ConversationShare,
    update_data: dict,
) -> ConversationShare:
    """Update a conversation share."""
    for field, value in update_data.items():
        setattr(db_share, field, value)
    db.add(db_share)
    await db.flush()
    await db.refresh(db_share)
    return db_share


async def delete(db: AsyncSession, share_id: UUID) -> bool:
    """Delete a share by ID."""
    share = await get_by_id(db, share_id)
    if not share:
        return False
    await db.delete(share)
    await db.flush()
    return True


{%- elif cookiecutter.use_sqlite %}
"""ConversationShare repository (SQLite sync)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DBSession

from app.db.models.conversation import Conversation
from app.db.models.conversation_share import ConversationShare


def get_by_id(db: DBSession, share_id: str) -> ConversationShare | None:
    """Get a share by ID."""
    return db.get(ConversationShare, share_id)


def get_share(
    db: DBSession, conversation_id: str, shared_with: str
) -> ConversationShare | None:
    """Get a share by conversation + user composite key."""
    result = db.execute(
        select(ConversationShare).where(
            ConversationShare.conversation_id == conversation_id,
            ConversationShare.shared_with == shared_with,
        )
    )
    return result.scalar_one_or_none()


def get_by_token(db: DBSession, token: str) -> ConversationShare | None:
    """Get a share by its public token."""
    result = db.execute(
        select(ConversationShare).where(ConversationShare.share_token == token)
    )
    return result.scalar_one_or_none()


def get_shares_for_conversation(
    db: DBSession, conversation_id: str
) -> list[ConversationShare]:
    """List all shares for a conversation."""
    result = db.execute(
        select(ConversationShare)
        .where(ConversationShare.conversation_id == conversation_id)
        .order_by(ConversationShare.created_at.desc())
    )
    return list(result.scalars().all())


def get_conversations_shared_with_user(
    db: DBSession, user_id: str, *, skip: int = 0, limit: int = 50
) -> list[Conversation]:
    """Get conversations shared with a specific user."""
    result = db.execute(
        select(Conversation)
        .join(ConversationShare, ConversationShare.conversation_id == Conversation.id)
        .where(ConversationShare.shared_with == user_id)
        .order_by(Conversation.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().all())


def count_conversations_shared_with_user(db: DBSession, user_id: str) -> int:
    """Count conversations shared with a specific user."""
    result = db.scalar(
        select(func.count())
        .select_from(ConversationShare)
        .where(ConversationShare.shared_with == user_id)
    )
    return result or 0


def user_has_access(
    db: DBSession, conversation_id: str, user_id: str
) -> ConversationShare | None:
    """Check if user has any share access to a conversation."""
    return get_share(db, conversation_id, user_id)


def create(
    db: DBSession,
    *,
    conversation_id: str,
    shared_by: str,
    shared_with: str | None = None,
    share_token: str | None = None,
    permission: str = "view",
) -> ConversationShare:
    """Create a new conversation share."""
    share = ConversationShare(
        conversation_id=conversation_id,
        shared_by=shared_by,
        shared_with=shared_with,
        share_token=share_token,
        permission=permission,
    )
    db.add(share)
    db.flush()
    db.refresh(share)
    return share


def update(
    db: DBSession,
    *,
    db_share: ConversationShare,
    update_data: dict,
) -> ConversationShare:
    """Update a conversation share."""
    for field, value in update_data.items():
        setattr(db_share, field, value)
    db.add(db_share)
    db.flush()
    db.refresh(db_share)
    return db_share


def delete(db: DBSession, share_id: str) -> bool:
    """Delete a share by ID."""
    share = get_by_id(db, share_id)
    if not share:
        return False
    db.delete(share)
    db.flush()
    return True


{%- elif cookiecutter.use_mongodb %}
"""ConversationShare repository (MongoDB)."""

from app.db.models.conversation import Conversation
from app.db.models.conversation_share import ConversationShare


async def get_by_id(share_id: str) -> ConversationShare | None:
    """Get a share by ID."""
    return await ConversationShare.get(share_id)


async def get_share(conversation_id: str, shared_with: str) -> ConversationShare | None:
    """Get a share by conversation + user composite key."""
    return await ConversationShare.find_one(
        ConversationShare.conversation_id == conversation_id,
        ConversationShare.shared_with == shared_with,
    )


async def get_by_token(token: str) -> ConversationShare | None:
    """Get a share by its public token."""
    return await ConversationShare.find_one(
        ConversationShare.share_token == token
    )


async def get_shares_for_conversation(conversation_id: str) -> list[ConversationShare]:
    """List all shares for a conversation."""
    return await ConversationShare.find(
        ConversationShare.conversation_id == conversation_id
    ).sort("-created_at").to_list()


async def get_conversations_shared_with_user(
    user_id: str, *, skip: int = 0, limit: int = 50
) -> list[Conversation]:
    """Get conversations shared with a specific user."""
    shares = await ConversationShare.find(
        ConversationShare.shared_with == user_id
    ).to_list()
    conv_ids = [s.conversation_id for s in shares]
    if not conv_ids:
        return []
    return (
        await Conversation.find({"_id": {"$in": conv_ids}})
        .sort("-updated_at")
        .skip(skip)
        .limit(limit)
        .to_list()
    )


async def count_conversations_shared_with_user(user_id: str) -> int:
    """Count conversations shared with a specific user."""
    return await ConversationShare.find(
        ConversationShare.shared_with == user_id
    ).count()


async def user_has_access(conversation_id: str, user_id: str) -> ConversationShare | None:
    """Check if user has any share access to a conversation."""
    return await get_share(conversation_id, user_id)


async def create(
    *,
    conversation_id: str,
    shared_by: str,
    shared_with: str | None = None,
    share_token: str | None = None,
    permission: str = "view",
) -> ConversationShare:
    """Create a new conversation share."""
    share = ConversationShare(
        conversation_id=conversation_id,
        shared_by=shared_by,
        shared_with=shared_with,
        share_token=share_token,
        permission=permission,
    )
    await share.insert()
    return share


async def update(
    *,
    db_share: ConversationShare,
    update_data: dict,
) -> ConversationShare:
    """Update a conversation share."""
    for field, value in update_data.items():
        setattr(db_share, field, value)
    await db_share.save()
    return db_share


async def delete(share_id: str) -> bool:
    """Delete a share by ID."""
    share = await get_by_id(share_id)
    if not share:
        return False
    await share.delete()
    return True


{%- else %}
"""ConversationShare repository — no supported database configured."""
{%- endif %}
{%- else %}
"""ConversationShare repository — requires JWT authentication (use_jwt)."""
{%- endif %}
