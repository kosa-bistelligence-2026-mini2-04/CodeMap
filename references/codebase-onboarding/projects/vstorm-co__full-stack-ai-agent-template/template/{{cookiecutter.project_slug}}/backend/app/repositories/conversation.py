{%- if cookiecutter.use_postgresql %}
"""Conversation repository (PostgreSQL async).

Contains database operations for Conversation, Message, and ToolCall entities.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import case, func, select, update as sql_update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
{%- if cookiecutter.use_jwt %}
from sqlalchemy import String
{%- endif %}

from app.db.models.conversation import Conversation, Message, ToolCall


# Conversation Operations


async def get_conversation_by_id(
    db: AsyncSession,
    conversation_id: UUID,
    *,
    include_messages: bool = False,
) -> Conversation | None:
    """Get conversation by ID, optionally with messages."""
    if include_messages:
        query = (
            select(Conversation)
            .options(
                selectinload(Conversation.messages).selectinload(Message.tool_calls),
                selectinload(Conversation.messages).selectinload(Message.files),
            )
            .where(Conversation.id == conversation_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    return await db.get(Conversation, conversation_id)


async def get_conversations_by_user(
    db: AsyncSession,
{%- if cookiecutter.use_jwt %}
    user_id: UUID | None = None,
{%- endif %}
{%- if cookiecutter.enable_teams %}
    organization_id: UUID | None = None,
{%- endif %}
    *,
    skip: int = 0,
    limit: int = 50,
    include_archived: bool = False,
) -> list[Conversation]:
    """Get conversations for a user with pagination."""
    query = select(Conversation)
{%- if cookiecutter.use_jwt %}
    if user_id:
        query = query.where(Conversation.user_id == user_id)
{%- endif %}
{%- if cookiecutter.enable_teams %}
    if organization_id is not None:
        query = query.where(Conversation.organization_id == organization_id)
{%- endif %}
    if not include_archived:
        query = query.where(Conversation.is_archived == False)  # noqa: E712
    query = query.order_by(func.coalesce(Conversation.updated_at, Conversation.created_at).desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


{%- if cookiecutter.use_jwt %}
async def get_all_conversations_with_count(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
    include_archived: bool = False,
    search: str | None = None,
) -> tuple[list[tuple[Conversation, int]], int]:
    """Get all conversations with message counts for admin (paginated).

    Returns list of (conversation, message_count) tuples and total count.
    """
    message_count_subq = (
        select(func.count(Message.id))
        .where(Message.conversation_id == Conversation.id)
        .correlate(Conversation)
        .scalar_subquery()
    )

    query = select(Conversation, message_count_subq.label("message_count"))

    if not include_archived:
        query = query.where(Conversation.is_archived == False)  # noqa: E712
    if search:
        safe_search = search.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
        query = query.where(
            (Conversation.title.ilike(f"%{safe_search}%", escape="\\"))
            | Conversation.id.cast(String).ilike(f"{safe_search}%", escape="\\")
        )

    query = query.order_by(
        func.coalesce(Conversation.updated_at, Conversation.created_at).desc()
    ).offset(skip).limit(limit)
    result = await db.execute(query)
    rows = result.all()

    # Total count (same filters, no pagination)
    count_query = select(func.count(Conversation.id))
    if not include_archived:
        count_query = count_query.where(Conversation.is_archived == False)  # noqa: E712
    if search:
        safe_search = search.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
        count_query = count_query.where(
            (Conversation.title.ilike(f"%{safe_search}%", escape="\\"))
            | Conversation.id.cast(String).ilike(f"{safe_search}%", escape="\\")
        )
    total: int = (await db.execute(count_query)).scalar() or 0

    return [tuple(row) for row in rows], total
{%- endif %}


{%- if cookiecutter.use_jwt %}


async def export_chunk(
    db: AsyncSession,
    *,
    last_created_at: datetime | None,
    last_id: UUID | None,
    limit: int,
) -> list[Conversation]:
    """Keyset-paginated chunk for admin export of all conversations."""
    from sqlalchemy import tuple_

    query = (
        select(Conversation)
        .order_by(Conversation.created_at.desc(), Conversation.id.desc())
        .limit(limit)
    )
    if last_created_at is not None and last_id is not None:
        query = query.where(
            tuple_(Conversation.created_at, Conversation.id) < (last_created_at, last_id)
        )
    result = await db.execute(query)
    return list(result.scalars().all())


async def admin_list_with_users(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    user_id: UUID | None = None,
    include_archived: bool = False,
    archived_only: bool = False,
    sort_by: str = "updated_at",
    sort_dir: str = "desc",
) -> tuple[list[tuple[Conversation, int, str | None]], int]:
    """Admin: list conversations across all users with message counts and owner email.

    Returns list of (conversation, message_count, user_email) tuples and total count.
    """
    from app.db.models.user import User

    msg_count_col = func.count(Message.id).label("message_count")
    query = (
        select(Conversation, msg_count_col, User.email.label("user_email"))
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .outerjoin(User, User.id == Conversation.user_id)
        .group_by(Conversation.id, User.email)
    )
    count_query = select(func.count()).select_from(Conversation)

    if search:
        query = query.where(Conversation.title.ilike(f"%{search}%"))
        count_query = count_query.where(Conversation.title.ilike(f"%{search}%"))
    if user_id is not None:
        query = query.where(Conversation.user_id == user_id)
        count_query = count_query.where(Conversation.user_id == user_id)
    if archived_only:
        query = query.where(Conversation.is_archived.is_(True))
        count_query = count_query.where(Conversation.is_archived.is_(True))
    elif not include_archived:
        query = query.where(Conversation.is_archived.is_(False))
        count_query = count_query.where(Conversation.is_archived.is_(False))

    sort_columns: dict[str, Any] = {
        "title": Conversation.title,
        "created_at": Conversation.created_at,
        "updated_at": Conversation.updated_at,
        "owner": User.email,
        "messages": msg_count_col,
    }
    sort_col = sort_columns.get(sort_by, Conversation.updated_at)
    sort_col = sort_col.desc() if sort_dir == "desc" else sort_col.asc()
    query = query.order_by(sort_col).offset(skip).limit(limit)

    total = await db.scalar(count_query) or 0
    rows = (await db.execute(query)).all()
    return [(conv, msg_count, email) for conv, msg_count, email in rows], total
{%- endif %}


async def count_conversations(
    db: AsyncSession,
{%- if cookiecutter.use_jwt %}
    user_id: UUID | None = None,
{%- endif %}
{%- if cookiecutter.enable_teams %}
    organization_id: UUID | None = None,
{%- endif %}
    *,
    include_archived: bool = False,
) -> int:
    """Count conversations for a user."""
    query = select(func.count(Conversation.id))
{%- if cookiecutter.use_jwt %}
    if user_id:
        query = query.where(Conversation.user_id == user_id)
{%- endif %}
{%- if cookiecutter.enable_teams %}
    if organization_id is not None:
        query = query.where(Conversation.organization_id == organization_id)
{%- endif %}
    if not include_archived:
        query = query.where(Conversation.is_archived == False)  # noqa: E712
    result = await db.execute(query)
    return result.scalar() or 0


async def create_conversation(
    db: AsyncSession,
    *,
{%- if cookiecutter.use_jwt %}
    user_id: UUID | None = None,
{%- endif %}
{%- if cookiecutter.use_external_user_id_in_conversations %}
    external_user_id: str | None = None,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    organization_id: UUID | None = None,
{%- endif %}
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
    project_id: UUID | None = None,
{%- endif %}
    title: str | None = None,
) -> Conversation:
    """Create a new conversation."""
    conversation = Conversation(
{%- if cookiecutter.use_jwt %}
        user_id=user_id,
{%- endif %}
{%- if cookiecutter.use_external_user_id_in_conversations %}
        external_user_id=external_user_id,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
        organization_id=organization_id,
{%- endif %}
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
        project_id=project_id,
{%- endif %}
        title=title,
    )
    db.add(conversation)
    await db.flush()
    await db.refresh(conversation)
    return conversation


{%- if cookiecutter.use_external_user_id_in_conversations %}


async def list_conversations_by_external_user_id(
    db: AsyncSession,
    external_user_id: str,
    *,
    skip: int = 0,
    limit: int = 50,
    include_archived: bool = False,
) -> list[Conversation]:
    """Fetch conversations by client-known IdP `sub` (delegated mode).

    Lets the client list a user's chats without ever knowing the internal
    User UUID. No FK join — direct index scan on the denormalized column.
    """
    query = select(Conversation).where(Conversation.external_user_id == external_user_id)
    if not include_archived:
        query = query.where(Conversation.is_archived == False)  # noqa: E712
    query = (
        query.order_by(Conversation.updated_at.desc().nullslast(), Conversation.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all())
{%- endif %}


async def update_conversation(
    db: AsyncSession,
    *,
    db_conversation: Conversation,
    update_data: dict[str, Any],
) -> Conversation:
    """Update a conversation."""
    for field, value in update_data.items():
        setattr(db_conversation, field, value)

    db.add(db_conversation)
    await db.flush()
    await db.refresh(db_conversation)
    return db_conversation


async def archive_conversation(
    db: AsyncSession,
    conversation_id: UUID,
) -> Conversation | None:
    """Archive a conversation."""
    conversation = await get_conversation_by_id(db, conversation_id)
    if conversation:
        conversation.is_archived = True
        db.add(conversation)
        await db.flush()
        await db.refresh(conversation)
    return conversation


async def delete_conversation(db: AsyncSession, conversation_id: UUID) -> bool:
    """Delete a conversation and all related messages/tool_calls (cascades)."""
    conversation = await get_conversation_by_id(db, conversation_id)
    if conversation:
        await db.delete(conversation)
        await db.flush()
        return True
    return False


# Message Operations


async def get_message_by_id(db: AsyncSession, message_id: UUID) -> Message | None:
    """Get message by ID."""
    return await db.get(Message, message_id)


async def get_messages_by_conversation(
    db: AsyncSession,
    conversation_id: UUID,
    *,
    skip: int = 0,
    limit: int = 100,
    include_tool_calls: bool = False,
) -> list[Message]:
    """Get messages for a conversation with pagination."""
    query = select(Message).where(Message.conversation_id == conversation_id)
    if include_tool_calls:
        query = query.options(selectinload(Message.tool_calls))
{%- if cookiecutter.use_jwt %}
    from app.db.models.chat_file import ChatFile
    query = query.options(selectinload(Message.files))
{%- endif %}
    query = query.order_by(Message.created_at.asc()).offset(skip).limit(limit)
    result = await db.execute(query)
    return list(result.scalars().all())


async def count_messages(db: AsyncSession, conversation_id: UUID) -> int:
    """Count messages in a conversation."""
    query = select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
    result = await db.execute(query)
    return result.scalar() or 0


async def create_message(
    db: AsyncSession,
    *,
    conversation_id: UUID,
    role: str,
    content: str,
    model_name: str | None = None,
    tokens_used: int | None = None,
) -> Message:
    """Create a new message."""
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        model_name=model_name,
        tokens_used=tokens_used,
    )
    db.add(message)
    await db.flush()
    await db.refresh(message)

    # Update conversation's updated_at timestamp
    await db.execute(
        sql_update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(updated_at=message.created_at)
    )

    return message


async def delete_message(db: AsyncSession, message_id: UUID) -> bool:
    """Delete a message."""
    message = await get_message_by_id(db, message_id)
    if message:
        await db.delete(message)
        await db.flush()
        return True
    return False


# ToolCall Operations

{%- if cookiecutter.enable_teams %}


async def aggregate_tool_calls_for_org(
    db: AsyncSession,
    organization_id: UUID,
    *,
    since: datetime,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Return per-tool aggregates for an org, ordered by call count desc.

    Joins ``tool_calls → messages → conversations`` so the same org filter the
    rest of the dashboard uses applies here. Excludes tool calls whose backing
    conversation has no ``organization_id`` (orphans).
    """
    query = (
        select(
            ToolCall.tool_name.label("tool_name"),
            func.count().label("total_calls"),
            func.sum(case((ToolCall.status == "failed", 1), else_=0)).label("failed_calls"),
            func.avg(ToolCall.duration_ms).label("avg_duration_ms"),
            func.max(ToolCall.started_at).label("last_used_at"),
        )
        .join(Message, Message.id == ToolCall.message_id)
        .join(Conversation, Conversation.id == Message.conversation_id)
        .where(
            Conversation.organization_id == organization_id,
            ToolCall.started_at >= since,
        )
        .group_by(ToolCall.tool_name)
        .order_by(func.count().desc())
        .limit(limit)
    )
    result = await db.execute(query)
    return [
        {
            "tool_name": row.tool_name,
            "total_calls": int(row.total_calls or 0),
            "failed_calls": int(row.failed_calls or 0),
            "avg_duration_ms": int(row.avg_duration_ms) if row.avg_duration_ms else None,
            "last_used_at": row.last_used_at,
        }
        for row in result.all()
    ]
{%- endif %}


async def get_tool_call_by_id(db: AsyncSession, tool_call_id: UUID) -> ToolCall | None:
    """Get tool call by ID."""
    return await db.get(ToolCall, tool_call_id)


async def get_tool_calls_by_message(
    db: AsyncSession,
    message_id: UUID,
) -> list[ToolCall]:
    """Get tool calls for a message."""
    query = (
        select(ToolCall)
        .where(ToolCall.message_id == message_id)
        .order_by(ToolCall.started_at.asc())
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def create_tool_call(
    db: AsyncSession,
    *,
    message_id: UUID,
    tool_call_id: str,
    tool_name: str,
    args: dict[str, Any],
    started_at: datetime,
) -> ToolCall:
    """Create a new tool call record."""
    tool_call = ToolCall(
        message_id=message_id,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        args=args,
        started_at=started_at,
        status="running",
    )
    db.add(tool_call)
    await db.flush()
    await db.refresh(tool_call)
    return tool_call


async def complete_tool_call(
    db: AsyncSession,
    *,
    db_tool_call: ToolCall,
    result: str,
    completed_at: datetime,
    success: bool = True,
) -> ToolCall:
    """Mark a tool call as completed."""
    db_tool_call.result = result
    db_tool_call.completed_at = completed_at
    db_tool_call.status = "completed" if success else "failed"

    # Calculate duration
    if db_tool_call.started_at:
        delta = completed_at - db_tool_call.started_at
        db_tool_call.duration_ms = int(delta.total_seconds() * 1000)

    db.add(db_tool_call)
    await db.flush()
    await db.refresh(db_tool_call)
    return db_tool_call


{%- elif cookiecutter.use_sqlite %}
"""Conversation repository (SQLite sync).

Contains database operations for Conversation, Message, and ToolCall entities.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import func, select, update as sql_update
from sqlalchemy.orm import Session, selectinload
{%- if cookiecutter.use_jwt %}
from sqlalchemy import String
{%- endif %}

from app.db.models.conversation import Conversation, Message, ToolCall


# Conversation Operations


def get_conversation_by_id(
    db: Session,
    conversation_id: str,
    *,
    include_messages: bool = False,
) -> Conversation | None:
    """Get conversation by ID, optionally with messages."""
    if include_messages:
        query = (
            select(Conversation)
            .options(selectinload(Conversation.messages).selectinload(Message.tool_calls))
            .where(Conversation.id == conversation_id)
        )
        result = db.execute(query)
        return result.scalar_one_or_none()
    return db.get(Conversation, conversation_id)


def get_conversations_by_user(
    db: Session,
{%- if cookiecutter.use_jwt %}
    user_id: str | None = None,
{%- endif %}
{%- if cookiecutter.enable_teams %}
    organization_id: str | None = None,
{%- endif %}
    *,
    skip: int = 0,
    limit: int = 50,
    include_archived: bool = False,
) -> list[Conversation]:
    """Get conversations for a user with pagination."""
    query = select(Conversation)
{%- if cookiecutter.use_jwt %}
    if user_id:
        query = query.where(Conversation.user_id == user_id)
{%- endif %}
{%- if cookiecutter.enable_teams %}
    if organization_id is not None:
        query = query.where(Conversation.organization_id == organization_id)
{%- endif %}
    if not include_archived:
        query = query.where(Conversation.is_archived == False)  # noqa: E712
    query = query.order_by(func.coalesce(Conversation.updated_at, Conversation.created_at).desc()).offset(skip).limit(limit)
    result = db.execute(query)
    return list(result.scalars().all())


{%- if cookiecutter.use_jwt %}
def get_all_conversations_with_count(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    include_archived: bool = False,
    search: str | None = None,
) -> tuple[list[tuple[Conversation, int]], int]:
    """Get all conversations with message counts for admin (paginated).

    Returns list of (conversation, message_count) tuples and total count.
    """
    message_count_subq = (
        select(func.count(Message.id))
        .where(Message.conversation_id == Conversation.id)
        .correlate(Conversation)
        .scalar_subquery()
    )

    query = select(Conversation, message_count_subq.label("message_count"))

    if not include_archived:
        query = query.where(Conversation.is_archived == False)  # noqa: E712
    if search:
        safe_search = search.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
        query = query.where(
            (Conversation.title.ilike(f"%{safe_search}%", escape="\\"))
            | Conversation.id.cast(String).ilike(f"{safe_search}%", escape="\\")
        )

    query = query.order_by(
        func.coalesce(Conversation.updated_at, Conversation.created_at).desc()
    ).offset(skip).limit(limit)
    result = db.execute(query)
    rows = result.all()

    # Total count (same filters, no pagination)
    count_query = select(func.count(Conversation.id))
    if not include_archived:
        count_query = count_query.where(Conversation.is_archived == False)  # noqa: E712
    if search:
        safe_search = search.replace("\\", "\\\\").replace("%", r"\%").replace("_", r"\_")
        count_query = count_query.where(
            (Conversation.title.ilike(f"%{safe_search}%", escape="\\"))
            | Conversation.id.cast(String).ilike(f"{safe_search}%", escape="\\")
        )
    total: int = db.execute(count_query).scalar() or 0

    return [tuple(row) for row in rows], total


def export_chunk(
    db: Session,
    *,
    last_created_at: datetime | None,
    last_id: str | None,
    limit: int,
) -> list[Conversation]:
    """Keyset-paginated chunk for admin export of all conversations."""
    from sqlalchemy import tuple_

    query = (
        select(Conversation)
        .order_by(Conversation.created_at.desc(), Conversation.id.desc())
        .limit(limit)
    )
    if last_created_at is not None and last_id is not None:
        query = query.where(
            tuple_(Conversation.created_at, Conversation.id) < (last_created_at, last_id)
        )
    result = db.execute(query)
    return list(result.scalars().all())


def admin_list_with_users(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    user_id: str | None = None,
    include_archived: bool = False,
    archived_only: bool = False,
    sort_by: str = "updated_at",
    sort_dir: str = "desc",
) -> tuple[list[tuple[Conversation, int, str | None]], int]:
    """Admin: list conversations across all users with message counts and owner email.

    Returns list of (conversation, message_count, user_email) tuples and total count.
    """
    from app.db.models.user import User

    msg_count_col = func.count(Message.id).label("message_count")
    query = (
        select(Conversation, msg_count_col, User.email.label("user_email"))
        .outerjoin(Message, Message.conversation_id == Conversation.id)
        .outerjoin(User, User.id == Conversation.user_id)
        .group_by(Conversation.id, User.email)
    )
    count_query = select(func.count()).select_from(Conversation)

    if search:
        query = query.where(Conversation.title.ilike(f"%{search}%"))
        count_query = count_query.where(Conversation.title.ilike(f"%{search}%"))
    if user_id is not None:
        query = query.where(Conversation.user_id == user_id)
        count_query = count_query.where(Conversation.user_id == user_id)
    if archived_only:
        query = query.where(Conversation.is_archived.is_(True))
        count_query = count_query.where(Conversation.is_archived.is_(True))
    elif not include_archived:
        query = query.where(Conversation.is_archived.is_(False))
        count_query = count_query.where(Conversation.is_archived.is_(False))

    sort_columns: dict[str, Any] = {
        "title": Conversation.title,
        "created_at": Conversation.created_at,
        "updated_at": Conversation.updated_at,
        "owner": User.email,
        "messages": msg_count_col,
    }
    sort_col = sort_columns.get(sort_by, Conversation.updated_at)
    sort_col = sort_col.desc() if sort_dir == "desc" else sort_col.asc()
    query = query.order_by(sort_col).offset(skip).limit(limit)

    total = db.scalar(count_query) or 0
    rows = db.execute(query).all()
    return [(conv, msg_count, email) for conv, msg_count, email in rows], total
{%- endif %}


def count_conversations(
    db: Session,
{%- if cookiecutter.use_jwt %}
    user_id: str | None = None,
{%- endif %}
{%- if cookiecutter.enable_teams %}
    organization_id: str | None = None,
{%- endif %}
    *,
    include_archived: bool = False,
) -> int:
    """Count conversations for a user."""
    query = select(func.count(Conversation.id))
{%- if cookiecutter.use_jwt %}
    if user_id:
        query = query.where(Conversation.user_id == user_id)
{%- endif %}
{%- if cookiecutter.enable_teams %}
    if organization_id is not None:
        query = query.where(Conversation.organization_id == organization_id)
{%- endif %}
    if not include_archived:
        query = query.where(Conversation.is_archived == False)  # noqa: E712
    result = db.execute(query)
    return result.scalar() or 0


def create_conversation(
    db: Session,
    *,
{%- if cookiecutter.use_jwt %}
    user_id: str | None = None,
{%- endif %}
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
    project_id: str | None = None,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    organization_id: str | None = None,
{%- endif %}
    title: str | None = None,
) -> Conversation:
    """Create a new conversation."""
    conversation = Conversation(
{%- if cookiecutter.use_jwt %}
        user_id=user_id,
{%- endif %}
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
        project_id=project_id,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
        organization_id=organization_id,
{%- endif %}
        title=title,
    )
    db.add(conversation)
    db.flush()
    db.refresh(conversation)
    return conversation


def update_conversation(
    db: Session,
    *,
    db_conversation: Conversation,
    update_data: dict[str, Any],
) -> Conversation:
    """Update a conversation."""
    for field, value in update_data.items():
        setattr(db_conversation, field, value)

    db.add(db_conversation)
    db.flush()
    db.refresh(db_conversation)
    return db_conversation


def archive_conversation(
    db: Session,
    conversation_id: str,
) -> Conversation | None:
    """Archive a conversation."""
    conversation = get_conversation_by_id(db, conversation_id)
    if conversation:
        conversation.is_archived = True
        db.add(conversation)
        db.flush()
        db.refresh(conversation)
    return conversation


def delete_conversation(db: Session, conversation_id: str) -> bool:
    """Delete a conversation and all related messages/tool_calls (cascades)."""
    conversation = get_conversation_by_id(db, conversation_id)
    if conversation:
        db.delete(conversation)
        db.flush()
        return True
    return False


# Message Operations


def get_message_by_id(db: Session, message_id: str) -> Message | None:
    """Get message by ID."""
    return db.get(Message, message_id)


def get_messages_by_conversation(
    db: Session,
    conversation_id: str,
    *,
    skip: int = 0,
    limit: int = 100,
    include_tool_calls: bool = False,
) -> list[Message]:
    """Get messages for a conversation with pagination."""
    query = select(Message).where(Message.conversation_id == conversation_id)
    if include_tool_calls:
        query = query.options(selectinload(Message.tool_calls))
{%- if cookiecutter.use_jwt %}
    from app.db.models.chat_file import ChatFile
    query = query.options(selectinload(Message.files))
{%- endif %}
    query = query.order_by(Message.created_at.asc()).offset(skip).limit(limit)
    result = db.execute(query)
    return list(result.scalars().all())


def count_messages(db: Session, conversation_id: str) -> int:
    """Count messages in a conversation."""
    query = select(func.count(Message.id)).where(Message.conversation_id == conversation_id)
    result = db.execute(query)
    return result.scalar() or 0


def create_message(
    db: Session,
    *,
    conversation_id: str,
    role: str,
    content: str,
    model_name: str | None = None,
    tokens_used: int | None = None,
) -> Message:
    """Create a new message."""
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        model_name=model_name,
        tokens_used=tokens_used,
    )
    db.add(message)
    db.flush()
    db.refresh(message)

    # Update conversation's updated_at timestamp
    db.execute(
        sql_update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(updated_at=message.created_at)
    )

    return message


def delete_message(db: Session, message_id: str) -> bool:
    """Delete a message."""
    message = get_message_by_id(db, message_id)
    if message:
        db.delete(message)
        db.flush()
        return True
    return False


# ToolCall Operations


def get_tool_call_by_id(db: Session, tool_call_id: str) -> ToolCall | None:
    """Get tool call by ID."""
    return db.get(ToolCall, tool_call_id)


def get_tool_calls_by_message(
    db: Session,
    message_id: str,
) -> list[ToolCall]:
    """Get tool calls for a message."""
    query = (
        select(ToolCall)
        .where(ToolCall.message_id == message_id)
        .order_by(ToolCall.started_at.asc())
    )
    result = db.execute(query)
    return list(result.scalars().all())


def create_tool_call(
    db: Session,
    *,
    message_id: str,
    tool_call_id: str,
    tool_name: str,
    args: dict[str, Any],
    started_at: datetime,
) -> ToolCall:
    """Create a new tool call record."""
    import json

    tool_call = ToolCall(
        message_id=message_id,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        args=json.dumps(args),  # SQLite stores as JSON string
        started_at=started_at,
        status="running",
    )
    db.add(tool_call)
    db.flush()
    db.refresh(tool_call)
    return tool_call


def deserialize_tool_call_args(tool_call: ToolCall) -> dict[str, Any]:
    """Deserialize tool call args from JSON string (SQLite stores as TEXT)."""
    import json

    if isinstance(tool_call.args, str):
        try:
            result: dict[str, Any] = json.loads(tool_call.args)
            return result
        except (json.JSONDecodeError, TypeError):
            return {}
    return dict(tool_call.args) if isinstance(tool_call.args, dict) else {}


def complete_tool_call(
    db: Session,
    *,
    db_tool_call: ToolCall,
    result: str,
    completed_at: datetime,
    success: bool = True,
) -> ToolCall:
    """Mark a tool call as completed."""
    db_tool_call.result = result
    db_tool_call.completed_at = completed_at
    db_tool_call.status = "completed" if success else "failed"

    # Calculate duration
    if db_tool_call.started_at:
        delta = completed_at - db_tool_call.started_at
        db_tool_call.duration_ms = int(delta.total_seconds() * 1000)

    db.add(db_tool_call)
    db.flush()
    db.refresh(db_tool_call)
    return db_tool_call


{%- elif cookiecutter.use_mongodb %}
"""Conversation repository (MongoDB).

Contains database operations for Conversation, Message, and ToolCall entities.
"""

from datetime import UTC, datetime
import re
from typing import Any

from app.db.models.conversation import Conversation, Message, ToolCall


# Conversation Operations


async def get_conversation_by_id(
    conversation_id: str,
    *,
    include_messages: bool = False,
) -> Conversation | None:
    """Get conversation by ID."""
    conversation = await Conversation.get(conversation_id)
    # Note: MongoDB doesn't auto-load related documents; handle in service layer
    return conversation


async def get_conversations_by_user(
{%- if cookiecutter.use_jwt %}
    user_id: str | None = None,
{%- endif %}
{%- if cookiecutter.enable_teams %}
    organization_id: str | None = None,
{%- endif %}
    *,
    skip: int = 0,
    limit: int = 50,
    include_archived: bool = False,
) -> list[Conversation]:
    """Get conversations for a user with pagination."""
    query_filter = {}
{%- if cookiecutter.use_jwt %}
    if user_id:
        query_filter["user_id"] = user_id
{%- endif %}
{%- if cookiecutter.enable_teams %}
    if organization_id is not None:
        query_filter["organization_id"] = organization_id
{%- endif %}
    if not include_archived:
        query_filter["is_archived"] = False

    return await Conversation.find(query_filter).sort("-created_at").skip(skip).limit(limit).to_list()


{%- if cookiecutter.use_jwt %}
async def get_all_conversations_with_count(
    *,
    skip: int = 0,
    limit: int = 50,
    include_archived: bool = False,
    search: str | None = None,
) -> tuple[list[tuple[Conversation, int]], int]:
    """Get all conversations with message counts for admin (paginated).

    Returns list of (conversation, message_count) tuples and total count.
    """
    pipeline: list[dict[str, Any]] = []

    # Match stage
    match_filter: dict[str, Any] = {}
    if not include_archived:
        match_filter["is_archived"] = False
    if search:
        # Add a string version of _id for prefix matching
        safe_search = re.escape(search)
        pipeline.append({"$addFields": {"_id_str": {"$toString": "$_id"}}})
        match_filter["$or"] = [
            {"title": {"$regex": safe_search, "$options": "i"}},
            {"_id_str": {"$regex": f"^{safe_search}", "$options": "i"}},
        ]
    if match_filter:
        pipeline.append({"$match": match_filter})

    # Lookup message counts
    pipeline.extend([
        {
            "$lookup": {
                "from": "messages",
                "localField": "_id",
                "foreignField": "conversation_id",
                "as": "msgs",
            }
        },
        {"$addFields": {"message_count": {"$size": "$msgs"}}},
        {"$project": {"msgs": 0}},
        {"$sort": {"updated_at": -1, "created_at": -1}},
        {"$skip": skip},
        {"$limit": limit},
    ])

    # Get conversations with counts
    conversations_raw = await Conversation.aggregate(pipeline).to_list()

    # Total count (use aggregation for consistent ID search via $toString)
    count_pipeline: list[dict[str, Any]] = []
    count_match: dict[str, Any] = {}
    if not include_archived:
        count_match["is_archived"] = False
    if count_match:
        count_pipeline.append({"$match": count_match})
    if search:
        safe_search = re.escape(search)
        count_pipeline.append({"$addFields": {"_id_str": {"$toString": "$_id"}}})
        count_pipeline.append({"$match": {"$or": [
            {"title": {"$regex": safe_search, "$options": "i"}},
            {"_id_str": {"$regex": f"^{safe_search}", "$options": "i"}},
        ]}})
    count_pipeline.append({"$count": "total"})
    count_result = await Conversation.aggregate(count_pipeline).to_list()
    total = count_result[0]["total"] if count_result else 0

    # Build result tuples: (conversation_obj, message_count)
    results: list[tuple[Conversation, int]] = []
    for doc in conversations_raw:
        conv = await Conversation.get(str(doc["_id"]))
        if conv:
            results.append((conv, doc.get("message_count", 0)))

    return results, total


async def admin_list_with_users(
    *,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    user_id: str | None = None,
    include_archived: bool = False,
    archived_only: bool = False,
    sort_by: str = "updated_at",
    sort_dir: str = "desc",
) -> tuple[list[tuple[Conversation, int, str | None]], int]:
    """Admin: list conversations with message counts and owner email.

    Returns list of (conversation, message_count, user_email) tuples and total count.
    """
    from app.db.models.user import User

    query_filter: dict[str, Any] = {}
    if search:
        query_filter["title"] = {"$regex": re.escape(search), "$options": "i"}
    if user_id:
        query_filter["user_id"] = user_id
    if archived_only:
        query_filter["is_archived"] = True
    elif not include_archived:
        query_filter["is_archived"] = False

    sort_field_map = {
        "title": "title",
        "created_at": "created_at",
        "updated_at": "updated_at",
    }
    sort_field = sort_field_map.get(sort_by, "updated_at")
    sort_prefix = "-" if sort_dir == "desc" else "+"

    total = await Conversation.find(query_filter).count()
    conversations = (
        await Conversation.find(query_filter)
        .sort(f"{sort_prefix}{sort_field}")
        .skip(skip)
        .limit(limit)
        .to_list()
    )

    results: list[tuple[Conversation, int, str | None]] = []
    for conv in conversations:
        msg_count = await Message.find(Message.conversation_id == str(conv.id)).count()
        user_email: str | None = None
        if conv.user_id:
            user = await User.get(conv.user_id)
            user_email = user.email if user else None
        results.append((conv, msg_count, user_email))
    return results, total
{%- endif %}


async def count_conversations(
{%- if cookiecutter.use_jwt %}
    user_id: str | None = None,
{%- endif %}
{%- if cookiecutter.enable_teams %}
    organization_id: str | None = None,
{%- endif %}
    *,
    include_archived: bool = False,
) -> int:
    """Count conversations for a user."""
    query_filter = {}
{%- if cookiecutter.use_jwt %}
    if user_id:
        query_filter["user_id"] = user_id
{%- endif %}
{%- if cookiecutter.enable_teams %}
    if organization_id is not None:
        query_filter["organization_id"] = organization_id
{%- endif %}
    if not include_archived:
        query_filter["is_archived"] = False

    return await Conversation.find(query_filter).count()


async def create_conversation(
    *,
{%- if cookiecutter.use_jwt %}
    user_id: str | None = None,
{%- endif %}
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
    project_id: str | None = None,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
    organization_id: str | None = None,
{%- endif %}
    title: str | None = None,
) -> Conversation:
    """Create a new conversation."""
    conversation = Conversation(
{%- if cookiecutter.use_jwt %}
        user_id=user_id,
{%- endif %}
{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
        project_id=project_id,
{%- endif %}
{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
        organization_id=organization_id,
{%- endif %}
        title=title,
    )
    await conversation.insert()
    return conversation


async def update_conversation(
    *,
    db_conversation: Conversation,
    update_data: dict[str, Any],
) -> Conversation:
    """Update a conversation."""
    for field, value in update_data.items():
        setattr(db_conversation, field, value)
    db_conversation.updated_at = datetime.now(UTC)
    await db_conversation.save()
    return db_conversation


async def archive_conversation(
    conversation_id: str,
) -> Conversation | None:
    """Archive a conversation."""
    conversation = await get_conversation_by_id(conversation_id)
    if conversation:
        conversation.is_archived = True
        conversation.updated_at = datetime.now(UTC)
        await conversation.save()
    return conversation


async def delete_conversation(conversation_id: str) -> bool:
    """Delete a conversation and all related messages/tool_calls."""
    conversation = await get_conversation_by_id(conversation_id)
    if conversation:
        # Delete related messages and tool calls
        messages = await get_messages_by_conversation(str(conversation.id))
        for message in messages:
            await ToolCall.find(ToolCall.message_id == str(message.id)).delete()
        await Message.find(Message.conversation_id == str(conversation.id)).delete()
        await conversation.delete()
        return True
    return False


# Message Operations


async def get_message_by_id(message_id: str) -> Message | None:
    """Get message by ID."""
    return await Message.get(message_id)


async def get_messages_by_conversation(
    conversation_id: str,
    *,
    skip: int = 0,
    limit: int = 100,
    include_tool_calls: bool = False,
) -> list[Message]:
    """Get messages for a conversation with pagination.

    MongoDB stores tool calls embedded in the message document, so
    `include_tool_calls` is accepted for API parity with the SQL variants
    but has no effect on the query.
    """
    del include_tool_calls  # embedded in Mongo message documents
    return await (
        Message.find(Message.conversation_id == conversation_id)
        .sort("created_at")
        .skip(skip)
        .limit(limit)
        .to_list()
    )


async def count_messages(conversation_id: str) -> int:
    """Count messages in a conversation."""
    return await Message.find(Message.conversation_id == conversation_id).count()


async def create_message(
    *,
    conversation_id: str,
    role: str,
    content: str,
    model_name: str | None = None,
    tokens_used: int | None = None,
) -> Message:
    """Create a new message."""
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        model_name=model_name,
        tokens_used=tokens_used,
    )
    await message.insert()

    # Update conversation's updated_at timestamp
    conversation = await get_conversation_by_id(conversation_id)
    if conversation:
        conversation.updated_at = datetime.now(UTC)
        await conversation.save()

    return message


async def delete_message(message_id: str) -> bool:
    """Delete a message and its tool calls."""
    message = await get_message_by_id(message_id)
    if message:
        await ToolCall.find(ToolCall.message_id == str(message.id)).delete()
        await message.delete()
        return True
    return False


# ToolCall Operations


async def get_tool_call_by_id(tool_call_id: str) -> ToolCall | None:
    """Get tool call by ID."""
    return await ToolCall.get(tool_call_id)


async def get_tool_calls_by_message(
    message_id: str,
) -> list[ToolCall]:
    """Get tool calls for a message."""
    return await (
        ToolCall.find(ToolCall.message_id == message_id)
        .sort("started_at")
        .to_list()
    )


async def create_tool_call(
    *,
    message_id: str,
    tool_call_id: str,
    tool_name: str,
    args: dict[str, Any],
    started_at: datetime,
) -> ToolCall:
    """Create a new tool call record."""
    tool_call = ToolCall(
        message_id=message_id,
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        args=args,
        started_at=started_at,
        status="running",
    )
    await tool_call.insert()
    return tool_call


async def complete_tool_call(
    *,
    db_tool_call: ToolCall,
    result: str,
    completed_at: datetime,
    success: bool = True,
) -> ToolCall:
    """Mark a tool call as completed."""
    db_tool_call.result = result
    db_tool_call.completed_at = completed_at
    db_tool_call.status = "completed" if success else "failed"

    # Calculate duration
    if db_tool_call.started_at:
        delta = completed_at - db_tool_call.started_at
        db_tool_call.duration_ms = int(delta.total_seconds() * 1000)

    await db_tool_call.save()
    return db_tool_call


{%- else %}
"""Conversation repository - not configured."""
{%- endif %}
