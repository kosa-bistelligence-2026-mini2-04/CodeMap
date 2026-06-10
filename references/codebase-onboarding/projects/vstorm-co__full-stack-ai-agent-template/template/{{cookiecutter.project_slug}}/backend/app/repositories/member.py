{%- if cookiecutter.enable_teams %}
{%- if cookiecutter.use_postgresql %}
"""OrganizationMember repository (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.organization import OrgRole, OrganizationMember


async def get(
    db: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
) -> OrganizationMember | None:
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def list_for_org(
    db: AsyncSession,
    organization_id: UUID,
    *,
    skip: int = 0,
    limit: int = 100,
) -> list[tuple[OrganizationMember, str, str | None, str | None]]:
    """Return (member, email, full_name, avatar_url) tuples ordered by join date."""
    from app.db.models.user import User

    result = await db.execute(
        select(OrganizationMember, User.email, User.full_name, User.avatar_url)
        .join(User, User.id == OrganizationMember.user_id)
        .where(OrganizationMember.organization_id == organization_id)
        .order_by(OrganizationMember.joined_at.asc())
        .offset(skip)
        .limit(limit)
    )
    return [(row[0], row[1], row[2], row[3]) for row in result.all()]


async def count_for_org(db: AsyncSession, organization_id: UUID) -> int:
    result = await db.execute(
        select(func.count(OrganizationMember.id)).where(
            OrganizationMember.organization_id == organization_id
        )
    )
    return result.scalar() or 0


async def count_billable_for_org(db: AsyncSession, organization_id: UUID) -> int:
    """Count billable members (Owner + Admin + Member; Viewer excluded)."""
    result = await db.execute(
        select(func.count(OrganizationMember.id)).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.role != OrgRole.VIEWER.value,
        )
    )
    return result.scalar() or 0


async def has_owner(db: AsyncSession, organization_id: UUID) -> bool:
    result = await db.execute(
        select(func.count(OrganizationMember.id)).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.role == OrgRole.OWNER.value,
        )
    )
    return (result.scalar() or 0) > 0


async def list_orgs_for_user(db: AsyncSession, user_id: UUID) -> list[OrganizationMember]:
    result = await db.execute(
        select(OrganizationMember).where(OrganizationMember.user_id == user_id)
    )
    return list(result.scalars().all())


async def create(
    db: AsyncSession,
    *,
    organization_id: UUID,
    user_id: UUID,
    role: str = OrgRole.MEMBER.value,
    invited_by_user_id: UUID | None = None,
) -> OrganizationMember:
    member = OrganizationMember(
        organization_id=organization_id,
        user_id=user_id,
        role=role,
        invited_by_user_id=invited_by_user_id,
    )
    db.add(member)
    await db.flush()
    await db.refresh(member)
    return member


async def update_role(
    db: AsyncSession,
    member: OrganizationMember,
    *,
    role: str,
) -> OrganizationMember:
    member.role = role
    await db.flush()
    await db.refresh(member)
    return member


async def delete(db: AsyncSession, member: OrganizationMember) -> None:
    await db.delete(member)
    await db.flush()


{%- elif cookiecutter.use_sqlite %}
"""OrganizationMember repository (SQLite sync)."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.organization import OrgRole, OrganizationMember


def get(db: Session, *, organization_id: str, user_id: str) -> OrganizationMember | None:
    return db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
    ).scalar_one_or_none()


def list_for_org(
    db: Session, organization_id: str, *, skip: int = 0, limit: int = 100
) -> list[tuple[OrganizationMember, str, str | None, str | None]]:
    """Return (member, email, full_name, avatar_url) tuples ordered by join date."""
    from app.db.models.user import User

    rows = db.execute(
        select(OrganizationMember, User.email, User.full_name, User.avatar_url)
        .join(User, User.id == OrganizationMember.user_id)
        .where(OrganizationMember.organization_id == organization_id)
        .order_by(OrganizationMember.joined_at.asc())
        .offset(skip)
        .limit(limit)
    ).all()
    return [(row[0], row[1], row[2], row[3]) for row in rows]


def count_for_org(db: Session, organization_id: str) -> int:
    return db.execute(
        select(func.count(OrganizationMember.id)).where(
            OrganizationMember.organization_id == organization_id
        )
    ).scalar() or 0


def count_billable_for_org(db: Session, organization_id: str) -> int:
    return db.execute(
        select(func.count(OrganizationMember.id)).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.role != OrgRole.VIEWER.value,
        )
    ).scalar() or 0


def has_owner(db: Session, organization_id: str) -> bool:
    return (db.execute(
        select(func.count(OrganizationMember.id)).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.role == OrgRole.OWNER.value,
        )
    ).scalar() or 0) > 0


def list_orgs_for_user(db: Session, user_id: str) -> list[OrganizationMember]:
    return list(
        db.execute(select(OrganizationMember).where(OrganizationMember.user_id == user_id)).scalars().all()
    )


def create(
    db: Session,
    *,
    organization_id: str,
    user_id: str,
    role: str = OrgRole.MEMBER.value,
    invited_by_user_id: str | None = None,
) -> OrganizationMember:
    member = OrganizationMember(
        organization_id=organization_id,
        user_id=user_id,
        role=role,
        invited_by_user_id=invited_by_user_id,
    )
    db.add(member)
    db.flush()
    db.refresh(member)
    return member


def update_role(db: Session, member: OrganizationMember, *, role: str) -> OrganizationMember:
    member.role = role
    db.flush()
    db.refresh(member)
    return member


def delete(db: Session, member: OrganizationMember) -> None:
    db.delete(member)
    db.flush()


{%- elif cookiecutter.use_mongodb %}
"""OrganizationMember repository (MongoDB)."""

from typing import Optional

from app.db.models.organization import OrgRole, OrganizationMember


async def get(*, organization_id: str, user_id: str) -> Optional[OrganizationMember]:
    return await OrganizationMember.find_one(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.user_id == user_id,
    )


async def list_for_org(
    organization_id: str, *, skip: int = 0, limit: int = 100
) -> list[tuple[OrganizationMember, str, str | None, str | None]]:
    """Return (member, email, full_name, avatar_url) tuples ordered by join date."""
    from app.db.models.user import User

    members = await OrganizationMember.find(
        OrganizationMember.organization_id == organization_id
    ).skip(skip).limit(limit).to_list()
    rows: list[tuple[OrganizationMember, str, str | None, str | None]] = []
    for m in members:
        user = await User.get(m.user_id)
        rows.append((m, user.email if user else "", user.full_name if user else None, user.avatar_url if user else None))
    return rows


async def count_for_org(organization_id: str) -> int:
    return await OrganizationMember.find(
        OrganizationMember.organization_id == organization_id
    ).count()


async def count_billable_for_org(organization_id: str) -> int:
    return await OrganizationMember.find(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.role != OrgRole.VIEWER.value,
    ).count()


async def has_owner(organization_id: str) -> bool:
    return await OrganizationMember.find_one(
        OrganizationMember.organization_id == organization_id,
        OrganizationMember.role == OrgRole.OWNER.value,
    ) is not None


async def list_orgs_for_user(user_id: str) -> list[OrganizationMember]:
    return await OrganizationMember.find(OrganizationMember.user_id == user_id).to_list()


async def create(
    *,
    organization_id: str,
    user_id: str,
    role: str = OrgRole.MEMBER.value,
    invited_by_user_id: Optional[str] = None,
) -> OrganizationMember:
    member = OrganizationMember(
        organization_id=organization_id,
        user_id=user_id,
        role=role,
        invited_by_user_id=invited_by_user_id,
    )
    await member.insert()
    return member


async def update_role(member: OrganizationMember, *, role: str) -> OrganizationMember:
    member.role = role
    await member.save()
    return member


async def delete(member: OrganizationMember) -> None:
    await member.delete()


{%- else %}
"""OrganizationMember repository — not configured."""
{%- endif %}
{%- else %}
"""OrganizationMember repository — not configured (enable_teams=false)."""
{%- endif %}
