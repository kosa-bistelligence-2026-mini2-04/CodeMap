"""Message rating repository for database operations."""

{%- if cookiecutter.use_postgresql %}
from datetime import datetime, timedelta, UTC
from typing import Any

from uuid import UUID

from sqlalchemy import Select, and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.message_rating import MessageRating


async def get_rating_by_message_and_user(
    db: AsyncSession,
    message_id: UUID,
    user_id: UUID,
) -> MessageRating | None:
    """Get a user's rating for a specific message."""
    query = select(MessageRating).where(
        MessageRating.message_id == message_id,
        MessageRating.user_id == user_id,
    )
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_rating(
    db: AsyncSession,
    *,
    message_id: UUID,
    user_id: UUID,
    rating: int,
    comment: str | None = None,
) -> MessageRating:
    """Create a new rating.

    Note: The unique constraint on (message_id, user_id) prevents duplicates
    at the database level. Callers should handle IntegrityError.
    """
    rating_obj = MessageRating(
        message_id=message_id,
        user_id=user_id,
        rating=rating,
        comment=comment,
    )
    db.add(rating_obj)
    await db.flush()
    await db.refresh(rating_obj)
    return rating_obj


async def update_rating(
    db: AsyncSession,
    rating: MessageRating,
    *,
    new_rating: int,
    comment: str | None = None,
) -> MessageRating:
    """Update an existing rating."""
    rating.rating = new_rating
    rating.comment = comment
    await db.flush()
    await db.refresh(rating)
    return rating


async def delete_rating(db: AsyncSession, rating: MessageRating) -> None:
    """Delete a rating."""
    await db.delete(rating)
    await db.flush()


async def get_ratings_for_message(
    db: AsyncSession,
    message_id: UUID,
) -> list[MessageRating]:
    """Get all ratings for a message."""
    query = select(MessageRating).where(
        MessageRating.message_id == message_id
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_user_ratings_for_messages(
    db: AsyncSession,
    *,
    message_ids: list[UUID],
    user_id: UUID,
) -> dict[UUID, int]:
    """Return mapping of message_id → rating value for a single user."""
    if not message_ids:
        return {}
    query = select(MessageRating).where(
        MessageRating.message_id.in_(message_ids),
        MessageRating.user_id == user_id,
    )
    result = await db.execute(query)
    return {rating.message_id: rating.rating for rating in result.scalars().all()}


async def get_rating_counts_for_messages(
    db: AsyncSession,
    *,
    message_ids: list[UUID],
) -> dict[UUID, dict[str, int]]:
    """Return mapping of message_id → {likes, dislikes} counts."""
    if not message_ids:
        return {}
    query = (
        select(
            MessageRating.message_id,
            func.sum(case((MessageRating.rating == 1, 1), else_=0)).label("likes"),
            func.sum(case((MessageRating.rating == -1, 1), else_=0)).label("dislikes"),
        )
        .where(MessageRating.message_id.in_(message_ids))
        .group_by(MessageRating.message_id)
    )
    result = await db.execute(query)
    return {
        row.message_id: {"likes": row.likes or 0, "dislikes": row.dislikes or 0}
        for row in result.all()
    }


async def get_ratings_with_users_for_messages(
    db: AsyncSession,
    *,
    message_ids: list[UUID],
) -> list[tuple[MessageRating, Any]]:
    """Return ratings joined with users for the given message IDs (admin export)."""
    if not message_ids:
        return []
    from app.db.models.user import User

    query = (
        select(MessageRating, User)
        .join(User, MessageRating.user_id == User.id)
        .where(MessageRating.message_id.in_(message_ids))
    )
    result = await db.execute(query)
    return [(rating, user) for rating, user in result.all()]


async def list_ratings(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 100,
    rating_filter: int | None = None,  # 1 or -1 to filter
    with_comments_only: bool = False,
) -> tuple[list[MessageRating], int]:
    """List ratings with optional filters."""
    query = select(MessageRating)

    if rating_filter is not None:
        query = query.where(MessageRating.rating == rating_filter)

    if with_comments_only:
        query = query.where(MessageRating.comment.isnot(None), MessageRating.comment != "")

    # Count query
    count_query = select(func.count()).select_from(query.subquery())
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    # Apply ordering and pagination
    query = query.order_by(MessageRating.created_at.desc()).offset(skip).limit(limit)

    # Eager load relationships
    query = query.options(
        selectinload(MessageRating.message),
{%- if cookiecutter.use_jwt %}
        selectinload(MessageRating.user),
{%- endif %}
    )

    result = await db.execute(query)
    items = list(result.scalars().all())

    return items, total


async def get_rating_summary(
    db: AsyncSession,
    *,
    days: int = 30,
) -> dict[str, Any]:
    """Get aggregated rating statistics."""
    cutoff_date = datetime.now(UTC) - timedelta(days=days)

    # Total counts
    counts_query = select(
        func.count().label("total"),
        func.sum(case((MessageRating.rating == 1, 1), else_=0)).label("likes"),
        func.sum(case((MessageRating.rating == -1, 1), else_=0)).label("dislikes"),
        func.avg(MessageRating.rating).label("avg_rating"),
        func.sum(case((and_(MessageRating.comment.isnot(None), MessageRating.comment != ""), 1), else_=0)).label("with_comments"),
    ).where(MessageRating.created_at >= cutoff_date)

    result = await db.execute(counts_query)
    row = result.one()

    # Daily breakdown
    daily_query = select(
        func.date(MessageRating.created_at).label("date"),
        func.sum(case((MessageRating.rating == 1, 1), else_=0)).label("likes"),
        func.sum(case((MessageRating.rating == -1, 1), else_=0)).label("dislikes"),
    ).where(
        MessageRating.created_at >= cutoff_date
    ).group_by(
        func.date(MessageRating.created_at)
    ).order_by(
        func.date(MessageRating.created_at)
    )

    daily_result = await db.execute(daily_query)
    ratings_by_day = [
        {"date": str(row.date), "likes": row.likes or 0, "dislikes": row.dislikes or 0}
        for row in daily_result
    ]

    return {
        "total_ratings": row.total or 0,
        "like_count": row.likes or 0,
        "dislike_count": row.dislikes or 0,
        "average_rating": float(row.avg_rating) if row.avg_rating else 0.0,
        "with_comments": row.with_comments or 0,
        "ratings_by_day": ratings_by_day,
    }


{%- elif cookiecutter.use_sqlite %}
"""Message rating repository (SQLite sync)."""

from datetime import datetime, timedelta, UTC
from typing import Any

from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session, selectinload

from app.db.models.message_rating import MessageRating


def get_rating_by_message_and_user(
    db: Session,
    message_id: str,
    user_id: str,
) -> MessageRating | None:
    """Get a user's rating for a specific message."""
    query = select(MessageRating).where(
        MessageRating.message_id == message_id,
        MessageRating.user_id == user_id,
    )
    result = db.execute(query)
    return result.scalar_one_or_none()


def create_rating(
    db: Session,
    *,
    message_id: str,
    user_id: str,
    rating: int,
    comment: str | None = None,
) -> MessageRating:
    """Create a new rating.

    Note: The unique constraint on (message_id, user_id) prevents duplicates
    at the database level. Callers should handle IntegrityError.
    """
    rating_obj = MessageRating(
        message_id=message_id,
        user_id=user_id,
        rating=rating,
        comment=comment,
    )
    db.add(rating_obj)
    db.flush()
    db.refresh(rating_obj)
    return rating_obj


def update_rating(
    db: Session,
    rating: MessageRating,
    *,
    new_rating: int,
    comment: str | None = None,
) -> MessageRating:
    """Update an existing rating."""
    rating.rating = new_rating
    rating.comment = comment
    db.flush()
    db.refresh(rating)
    return rating


def delete_rating(db: Session, rating: MessageRating) -> None:
    """Delete a rating."""
    db.delete(rating)
    db.flush()


def get_ratings_for_message(
    db: Session,
    message_id: str,
) -> list[MessageRating]:
    """Get all ratings for a message."""
    query = select(MessageRating).where(
        MessageRating.message_id == message_id
    )
    result = db.execute(query)
    return list(result.scalars().all())


def get_user_ratings_for_messages(
    db: Session,
    *,
    message_ids: list[str],
    user_id: str,
) -> dict[str, int]:
    """Return mapping of message_id → rating value for a single user."""
    if not message_ids:
        return {}
    query = select(MessageRating).where(
        MessageRating.message_id.in_(message_ids),
        MessageRating.user_id == user_id,
    )
    result = db.execute(query)
    return {rating.message_id: rating.rating for rating in result.scalars().all()}


def get_rating_counts_for_messages(
    db: Session,
    *,
    message_ids: list[str],
) -> dict[str, dict[str, int]]:
    """Return mapping of message_id → {likes, dislikes} counts."""
    if not message_ids:
        return {}
    query = (
        select(
            MessageRating.message_id,
            func.sum(case((MessageRating.rating == 1, 1), else_=0)).label("likes"),
            func.sum(case((MessageRating.rating == -1, 1), else_=0)).label("dislikes"),
        )
        .where(MessageRating.message_id.in_(message_ids))
        .group_by(MessageRating.message_id)
    )
    result = db.execute(query)
    return {
        row.message_id: {"likes": row.likes or 0, "dislikes": row.dislikes or 0}
        for row in result.all()
    }


def get_ratings_with_users_for_messages(
    db: Session,
    *,
    message_ids: list[str],
) -> list[tuple[MessageRating, Any]]:
    """Return ratings joined with users for the given message IDs (admin export)."""
    if not message_ids:
        return []
    from app.db.models.user import User

    query = (
        select(MessageRating, User)
        .join(User, MessageRating.user_id == User.id)
        .where(MessageRating.message_id.in_(message_ids))
    )
    result = db.execute(query)
    return [(rating, user) for rating, user in result.all()]


def list_ratings(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    rating_filter: int | None = None,
    with_comments_only: bool = False,
) -> tuple[list[MessageRating], int]:
    """List ratings with optional filters."""
    query = select(MessageRating)

    if rating_filter is not None:
        query = query.where(MessageRating.rating == rating_filter)

    if with_comments_only:
        query = query.where(MessageRating.comment.isnot(None), MessageRating.comment != "")

    # Count query
    count_query = select(func.count()).select_from(query.subquery())
    count_result = db.execute(count_query)
    total = count_result.scalar_one()

    # Apply ordering and pagination
    query = query.order_by(MessageRating.created_at.desc()).offset(skip).limit(limit)

    # Eager load relationships
    query = query.options(
        selectinload(MessageRating.message),
{%- if cookiecutter.use_jwt %}
        selectinload(MessageRating.user),
{%- endif %}
    )

    result = db.execute(query)
    items = list(result.scalars().all())

    return items, total


def get_rating_summary(
    db: Session,
    *,
    days: int = 30,
) -> dict[str, Any]:
    """Get aggregated rating statistics."""
    cutoff_date = datetime.now(UTC) - timedelta(days=days)

    # Total counts
    counts_query = select(
        func.count().label("total"),
        func.sum(case((MessageRating.rating == 1, 1), else_=0)).label("likes"),
        func.sum(case((MessageRating.rating == -1, 1), else_=0)).label("dislikes"),
        func.avg(MessageRating.rating).label("avg_rating"),
        func.sum(case((and_(MessageRating.comment.isnot(None), MessageRating.comment != ""), 1), else_=0)).label("with_comments"),
    ).where(MessageRating.created_at >= cutoff_date)

    result = db.execute(counts_query)
    row = result.one()

    # Daily breakdown
    daily_query = select(
        func.date(MessageRating.created_at).label("date"),
        func.sum(case((MessageRating.rating == 1, 1), else_=0)).label("likes"),
        func.sum(case((MessageRating.rating == -1, 1), else_=0)).label("dislikes"),
    ).where(
        MessageRating.created_at >= cutoff_date
    ).group_by(
        func.date(MessageRating.created_at)
    ).order_by(
        func.date(MessageRating.created_at)
    )

    daily_result = db.execute(daily_query)
    ratings_by_day = [
        {"date": str(row.date), "likes": row.likes or 0, "dislikes": row.dislikes or 0}
        for row in daily_result
    ]

    return {
        "total_ratings": row.total or 0,
        "like_count": row.likes or 0,
        "dislike_count": row.dislikes or 0,
        "average_rating": float(row.avg_rating) if row.avg_rating else 0.0,
        "with_comments": row.with_comments or 0,
        "ratings_by_day": ratings_by_day,
    }


{%- elif cookiecutter.use_mongodb %}
"""Message rating repository (MongoDB async)."""

from datetime import datetime, timedelta, UTC
from typing import Any

from app.db.models.message_rating import MessageRating


async def get_rating_by_message_and_user(
    message_id: str,
    user_id: str,
) -> MessageRating | None:
    """Get a user's rating for a specific message."""
    return await MessageRating.find_one(
        {"message_id": message_id, "user_id": user_id}
    )


async def create_rating(
    *,
    message_id: str,
    conversation_id: str,
    user_id: str,
    rating: int,
    comment: str | None = None,
) -> MessageRating:
    """Create a new rating.

    Uses findOneAndUpdate with upsert to prevent race conditions.
    """
    from pymongo import ReturnDocument

    now = datetime.now(UTC)
    result = await MessageRating.get_motor_collection().find_one_and_update(
        {"message_id": message_id, "user_id": user_id},
        {
            "$set": {
                "message_id": message_id,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "rating": rating,
                "comment": comment,
                "created_at": now,
                "updated_at": now,  # Set updated_at on creation
            }
        },
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    return MessageRating.model_validate(result)


async def update_rating(
    rating: MessageRating,
    *,
    new_rating: int,
    comment: str | None = None,
) -> MessageRating:
    """Update an existing rating."""
    from pymongo import ReturnDocument

    now = datetime.now(UTC)
    result = await MessageRating.get_motor_collection().find_one_and_update(
        {"_id": rating.id},
        {
            "$set": {
                "rating": new_rating,
                "comment": comment,
                "updated_at": now,
            }
        },
        return_document=ReturnDocument.AFTER,
    )

    return MessageRating.model_validate(result)


async def delete_rating(rating: MessageRating) -> None:
    """Delete a rating."""
    await rating.delete()


async def get_ratings_for_message(
    message_id: str,
) -> list[MessageRating]:
    """Get all ratings for a message."""
    return await MessageRating.find({"message_id": message_id}).to_list()


async def list_ratings(
    *,
    skip: int = 0,
    limit: int = 100,
    rating_filter: int | None = None,
    with_comments_only: bool = False,
) -> tuple[list[MessageRating], int]:
    """List ratings with optional filters."""
    query_dict: dict[str, Any] = {}

    if rating_filter is not None:
        query_dict["rating"] = rating_filter

    if with_comments_only:
        query_dict["comment"] = {"$nin": [None, ""]}

    # Count and fetch in parallel
    total_future = MessageRating.find(query_dict).count()
    items_future = MessageRating.find(query_dict).sort("-created_at").skip(skip).limit(limit).to_list()

    total = await total_future
    items = await items_future

    return items, total


async def get_rating_summary(
    *,
    days: int = 30,
) -> dict[str, Any]:
    """Get aggregated rating statistics."""
    cutoff_date = datetime.now(UTC) - timedelta(days=days)

    pipeline = [
        {"$match": {"created_at": {"$gte": cutoff_date}}},
        {
            "$group": {
                "_id": None,
                "total": {"$sum": 1},
                "likes": {
                    "$sum": {"$cond": [{"$eq": ["$rating", 1]}, 1, 0]}
                },
                "dislikes": {
                    "$sum": {"$cond": [{"$eq": ["$rating", -1]}, 1, 0]}
                },
                "avg_rating": {"$avg": "$rating"},
                "with_comments": {
                    "$sum": {"$cond": [{"$and": [
                        {"$ne": ["$comment", None]},
                        {"$ne": ["$comment", ""]}
                    ]}, 1, 0]}
                },
            }
        },
    ]

    result = await MessageRating.aggregate(pipeline).to_list(None)
    summary = result[0] if result else {
        "total": 0, "likes": 0, "dislikes": 0, "avg_rating": 0, "with_comments": 0
    }

    # Daily breakdown
    daily_pipeline = [
        {"$match": {"created_at": {"$gte": cutoff_date}}},
        {
            "$group": {
                "_id": {
                    "date": {
                        "$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}
                    }
                },
                "likes": {
                    "$sum": {"$cond": [{"$eq": ["$rating", 1]}, 1, 0]}
                },
                "dislikes": {
                    "$sum": {"$cond": [{"$eq": ["$rating", -1]}, 1, 0]}
                },
            }
        },
        {"$sort": {"_id.date": 1}},
        {
            "$project": {
                "date": "$_id.date",
                "likes": 1,
                "dislikes": 1,
                "_id": 0,
            }
        },
    ]

    ratings_by_day = await MessageRating.aggregate(daily_pipeline).to_list(None)

    return {
        "total_ratings": summary.get("total", 0),
        "like_count": summary.get("likes", 0),
        "dislike_count": summary.get("dislikes", 0),
        "average_rating": summary.get("avg_rating", 0.0),
        "with_comments": summary.get("with_comments", 0),
        "ratings_by_day": ratings_by_day,
    }


{%- endif %}
