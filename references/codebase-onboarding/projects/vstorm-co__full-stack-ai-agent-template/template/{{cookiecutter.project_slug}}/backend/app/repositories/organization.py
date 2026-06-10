{%- if cookiecutter.enable_teams %}
{%- if cookiecutter.use_postgresql %}
"""Organization repository (PostgreSQL async)."""

import re
import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.organization import Organization


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:64] or "org"


async def get_by_id(db: AsyncSession, org_id: UUID) -> Organization | None:
    return await db.get(Organization, org_id)


async def get_by_slug(db: AsyncSession, slug: str) -> Organization | None:
    result = await db.execute(select(Organization).where(Organization.slug == slug))
    return result.scalar_one_or_none()


async def get_personal_for_user(db: AsyncSession, user_id: UUID) -> Organization | None:
    result = await db.execute(
        select(Organization).where(
            Organization.created_by_user_id == user_id,
            Organization.is_personal.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def list_for_user(db: AsyncSession, user_id: UUID) -> list[Organization]:
    from app.db.models.organization import OrganizationMember

    result = await db.execute(
        select(Organization)
        .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
        .where(OrganizationMember.user_id == user_id)
        .order_by(Organization.is_personal.desc(), Organization.created_at.asc())
    )
    return list(result.scalars().all())


async def slug_exists(db: AsyncSession, slug: str) -> bool:
    result = await db.execute(select(func.count(Organization.id)).where(Organization.slug == slug))
    return (result.scalar() or 0) > 0


async def generate_unique_slug(db: AsyncSession, base: str) -> str:
    candidate = _slugify(base)
    if not await slug_exists(db, candidate):
        return candidate
    for i in range(2, 100):
        suffixed = f"{candidate}-{i}"
        if not await slug_exists(db, suffixed):
            return suffixed
    return f"{candidate}-{uuid.uuid4().hex[:6]}"


async def create(
    db: AsyncSession,
    *,
    name: str,
    slug: str,
    created_by_user_id: UUID,
    is_personal: bool = False,
    avatar_url: str | None = None,
) -> Organization:
    org = Organization(
        name=name,
        slug=slug,
        created_by_user_id=created_by_user_id,
        is_personal=is_personal,
        avatar_url=avatar_url,
    )
    db.add(org)
    await db.flush()
    await db.refresh(org)
    return org


async def update(
    db: AsyncSession,
    org: Organization,
    *,
    name: str | None = None,
    avatar_url: str | None = None,
) -> Organization:
    if name is not None:
        org.name = name
    if avatar_url is not None:
        org.avatar_url = avatar_url
    await db.flush()
    await db.refresh(org)
    return org


async def delete(db: AsyncSession, org: Organization) -> None:
    await db.delete(org)
    await db.flush()


async def count_members(db: AsyncSession, org_id: UUID) -> int:
    from app.db.models.organization import OrganizationMember

    result = await db.execute(
        select(func.count(OrganizationMember.id)).where(
            OrganizationMember.organization_id == org_id
        )
    )
    return result.scalar() or 0

{%- if cookiecutter.enable_billing %}


async def get_by_stripe_customer(db: AsyncSession, customer_id: str) -> Organization | None:
    result = await db.execute(
        select(Organization).where(Organization.stripe_customer_id == customer_id)
    )
    return result.scalar_one_or_none()


async def update_billing(
    db: AsyncSession,
    *,
    db_org: Organization,
    update_data: dict,
) -> Organization:
    for field, value in update_data.items():
        setattr(db_org, field, value)
    await db.flush()
    await db.refresh(db_org)
    return db_org
{%- endif %}

{%- if cookiecutter.enable_credits_system %}


async def get_with_low_credits(
    db: AsyncSession, *, threshold: int
) -> list[tuple[Organization, str, str]]:
    """Return (org, owner_email, owner_name) for orgs with credits below threshold."""
    from app.db.models.organization import OrganizationMember
    from app.db.models.user import User

    result = await db.execute(
        select(Organization, User.email, User.full_name)
        .join(
            OrganizationMember,
            (OrganizationMember.organization_id == Organization.id)
            & (OrganizationMember.role == "owner"),
        )
        .join(User, User.id == OrganizationMember.user_id)
        .where(
            Organization.credits_balance >= 0,
            Organization.credits_balance < threshold,
        )
    )
    return [(row[0], row[1], row[2] or row[1]) for row in result.all()]
{%- endif %}


{%- elif cookiecutter.use_sqlite %}
"""Organization repository (SQLite sync)."""

import re
import uuid
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models.organization import Organization


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:64] or "org"


def get_by_id(db: Session, org_id: str) -> Organization | None:
    return db.get(Organization, org_id)


def get_by_slug(db: Session, slug: str) -> Organization | None:
    return db.execute(select(Organization).where(Organization.slug == slug)).scalar_one_or_none()


def get_personal_for_user(db: Session, user_id: str) -> Organization | None:
    return db.execute(
        select(Organization).where(
            Organization.created_by_user_id == user_id,
            Organization.is_personal.is_(True),
        )
    ).scalar_one_or_none()


def list_for_user(db: Session, user_id: str) -> list[Organization]:
    from app.db.models.organization import OrganizationMember

    return list(
        db.execute(
            select(Organization)
            .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
            .where(OrganizationMember.user_id == user_id)
            .order_by(Organization.is_personal.desc(), Organization.created_at.asc())
        ).scalars().all()
    )


def slug_exists(db: Session, slug: str) -> bool:
    return (db.execute(select(func.count(Organization.id)).where(Organization.slug == slug)).scalar() or 0) > 0


def generate_unique_slug(db: Session, base: str) -> str:
    candidate = _slugify(base)
    if not slug_exists(db, candidate):
        return candidate
    for i in range(2, 100):
        suffixed = f"{candidate}-{i}"
        if not slug_exists(db, suffixed):
            return suffixed
    return f"{candidate}-{uuid.uuid4().hex[:6]}"


def create(
    db: Session,
    *,
    name: str,
    slug: str,
    created_by_user_id: str,
    is_personal: bool = False,
    avatar_url: str | None = None,
) -> Organization:
    org = Organization(
        name=name,
        slug=slug,
        created_by_user_id=created_by_user_id,
        is_personal=is_personal,
        avatar_url=avatar_url,
    )
    db.add(org)
    db.flush()
    db.refresh(org)
    return org


def update(
    db: Session,
    org: Organization,
    *,
    name: str | None = None,
    avatar_url: str | None = None,
) -> Organization:
    if name is not None:
        org.name = name
    if avatar_url is not None:
        org.avatar_url = avatar_url
    db.flush()
    db.refresh(org)
    return org


def delete(db: Session, org: Organization) -> None:
    db.delete(org)
    db.flush()


def count_members(db: Session, org_id: str) -> int:
    from app.db.models.organization import OrganizationMember

    return db.execute(
        select(func.count(OrganizationMember.id)).where(OrganizationMember.organization_id == org_id)
    ).scalar() or 0

{%- if cookiecutter.enable_billing %}


def get_by_stripe_customer(db: Session, customer_id: str) -> Organization | None:
    return db.execute(
        select(Organization).where(Organization.stripe_customer_id == customer_id)
    ).scalar_one_or_none()


def update_billing(
    db: Session,
    *,
    db_org: Organization,
    update_data: dict,
) -> Organization:
    for field, value in update_data.items():
        setattr(db_org, field, value)
    db.flush()
    db.refresh(db_org)
    return db_org
{%- endif %}

{%- if cookiecutter.enable_credits_system %}


def get_with_low_credits(
    db: Session, *, threshold: int
) -> list[tuple[Organization, str, str]]:
    """Return (org, owner_email, owner_name) for orgs with credits below threshold."""
    from app.db.models.organization import OrganizationMember
    from app.db.models.user import User

    result = db.execute(
        select(Organization, User.email, User.full_name)
        .join(
            OrganizationMember,
            (OrganizationMember.organization_id == Organization.id)
            & (OrganizationMember.role == "owner"),
        )
        .join(User, User.id == OrganizationMember.user_id)
        .where(
            Organization.credits_balance >= 0,
            Organization.credits_balance < threshold,
        )
    )
    return [(row[0], row[1], row[2] or row[1]) for row in result.all()]
{%- endif %}


{%- elif cookiecutter.use_mongodb %}
"""Organization repository (MongoDB)."""

import re
import uuid
from typing import Optional

from app.db.models.organization import Organization


def _slugify(text: str) -> str:
    slug = text.lower().strip()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = re.sub(r"[\s_]+", "-", slug)
    slug = re.sub(r"-+", "-", slug)
    return slug.strip("-")[:64] or "org"


async def get_by_id(org_id: str) -> Optional[Organization]:
    return await Organization.get(org_id)


async def get_by_slug(slug: str) -> Optional[Organization]:
    return await Organization.find_one(Organization.slug == slug)


async def get_personal_for_user(user_id: str) -> Optional[Organization]:
    return await Organization.find_one(
        Organization.created_by_user_id == user_id,
        Organization.is_personal == True,  # noqa: E712
    )


async def list_for_user(user_id: str) -> list[Organization]:
    from app.db.models.organization import OrganizationMember

    members = await OrganizationMember.find(OrganizationMember.user_id == user_id).to_list()
    org_ids = [m.organization_id for m in members]
    if not org_ids:
        return []
    return await Organization.find({"_id": {"$in": org_ids}}).to_list()


async def slug_exists(slug: str) -> bool:
    return await Organization.find_one(Organization.slug == slug) is not None


async def generate_unique_slug(base: str) -> str:
    candidate = _slugify(base)
    if not await slug_exists(candidate):
        return candidate
    for i in range(2, 100):
        suffixed = f"{candidate}-{i}"
        if not await slug_exists(suffixed):
            return suffixed
    return f"{candidate}-{uuid.uuid4().hex[:6]}"


async def create(
    *,
    name: str,
    slug: str,
    created_by_user_id: str,
    is_personal: bool = False,
    avatar_url: Optional[str] = None,
) -> Organization:
    org = Organization(
        name=name,
        slug=slug,
        created_by_user_id=created_by_user_id,
        is_personal=is_personal,
        avatar_url=avatar_url,
    )
    await org.insert()
    return org


async def delete(org: Organization) -> None:
    await org.delete()

{%- if cookiecutter.enable_credits_system %}


async def get_with_low_credits(
    _db: Any, *, threshold: int
) -> list[tuple["Organization", str, str]]:
    """Return (org, owner_email, owner_name) for orgs with credits below threshold."""
    from app.db.models.organization import OrganizationMember
    from app.db.models.user import User

    orgs = await Organization.find(
        Organization.credits_balance >= 0,
        Organization.credits_balance < threshold,
    ).to_list()

    result = []
    for org in orgs:
        member = await OrganizationMember.find_one(
            OrganizationMember.organization_id == str(org.id),
            OrganizationMember.role == "owner",
        )
        if not member:
            continue
        user = await User.get(member.user_id)
        if not user:
            continue
        result.append((org, user.email, user.full_name or user.email))
    return result
{%- endif %}


{%- else %}
"""Organization repository — not configured."""
{%- endif %}
{%- else %}
"""Organization repository — not configured (enable_teams=false)."""
{%- endif %}
