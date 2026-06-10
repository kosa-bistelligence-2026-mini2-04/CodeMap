{%- if cookiecutter.enable_teams and cookiecutter.enable_rag and cookiecutter.use_jwt %}
{%- if cookiecutter.use_postgresql %}
"""Knowledge Base repository (PostgreSQL async)."""

from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.knowledge_base import KBScope, KnowledgeBase


async def get_by_id(db: AsyncSession, kb_id: UUID) -> KnowledgeBase | None:
    return await db.get(KnowledgeBase, kb_id)


async def get_accessible(
    db: AsyncSession,
    *,
    user_id: UUID,
    organization_id: UUID | None = None,
) -> list[KnowledgeBase]:
    """All KBs visible to this user: personal + org (if org given) + app."""
    conditions = [
        # personal: owned by this user
        (KnowledgeBase.scope == KBScope.PERSONAL.value) & (KnowledgeBase.owner_user_id == user_id),
        # app: global
        KnowledgeBase.scope == KBScope.APP.value,
    ]
    if organization_id is not None:
        conditions.append(
            (KnowledgeBase.scope == KBScope.ORG.value) & (KnowledgeBase.organization_id == organization_id)
        )
    result = await db.execute(
        select(KnowledgeBase).where(or_(*conditions)).order_by(KnowledgeBase.created_at)
    )
    return list(result.scalars().all())


async def get_default_for_org(db: AsyncSession, organization_id: UUID) -> KnowledgeBase | None:
    result = await db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.organization_id == organization_id,
            KnowledgeBase.scope == KBScope.ORG.value,
            KnowledgeBase.is_default.is_(True),
        )
    )
    return result.scalar_one_or_none()


async def get_documents_count(db: AsyncSession, kb_id: UUID) -> int:
    from sqlalchemy import func
    from app.db.models.rag_document import RAGDocument
    result = await db.execute(
        select(func.count(RAGDocument.id)).where(RAGDocument.knowledge_base_id == kb_id)
    )
    return result.scalar() or 0


async def create(
    db: AsyncSession,
    *,
    name: str,
    collection_name: str,
    scope: str,
    description: str | None = None,
    owner_user_id: UUID | None = None,
    organization_id: UUID | None = None,
    is_default: bool = False,
) -> KnowledgeBase:
    kb = KnowledgeBase(
        name=name,
        collection_name=collection_name,
        scope=scope,
        description=description,
        owner_user_id=owner_user_id,
        organization_id=organization_id,
        is_default=is_default,
    )
    db.add(kb)
    await db.flush()
    await db.refresh(kb)
    return kb


async def update(
    db: AsyncSession,
    *,
    db_kb: KnowledgeBase,
    name: str | None = None,
    description: str | None = None,
) -> KnowledgeBase:
    if name is not None:
        db_kb.name = name
    if description is not None:
        db_kb.description = description
    await db.flush()
    await db.refresh(db_kb)
    return db_kb


async def delete(db: AsyncSession, kb_id: UUID) -> bool:
    kb = await db.get(KnowledgeBase, kb_id)
    if not kb:
        return False
    await db.delete(kb)
    await db.flush()
    return True

{%- elif cookiecutter.use_sqlite %}
"""Knowledge Base repository (SQLite sync)."""

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models.knowledge_base import KBScope, KnowledgeBase


def get_by_id(db: Session, kb_id: str) -> KnowledgeBase | None:
    return db.get(KnowledgeBase, kb_id)


def get_accessible(
    db: Session,
    *,
    user_id: str,
    organization_id: str | None = None,
) -> list[KnowledgeBase]:
    """All KBs visible to this user: personal + org (if org given) + app."""
    conditions = [
        (KnowledgeBase.scope == KBScope.PERSONAL.value) & (KnowledgeBase.owner_user_id == user_id),
        KnowledgeBase.scope == KBScope.APP.value,
    ]
    if organization_id is not None:
        conditions.append(
            (KnowledgeBase.scope == KBScope.ORG.value) & (KnowledgeBase.organization_id == organization_id)
        )
    result = db.execute(
        select(KnowledgeBase).where(or_(*conditions)).order_by(KnowledgeBase.created_at)
    )
    return list(result.scalars().all())


def get_default_for_org(db: Session, organization_id: str) -> KnowledgeBase | None:
    result = db.execute(
        select(KnowledgeBase).where(
            KnowledgeBase.organization_id == organization_id,
            KnowledgeBase.scope == KBScope.ORG.value,
            KnowledgeBase.is_default == True,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


def get_documents_count(db: Session, kb_id: str) -> int:
    from sqlalchemy import func
    from app.db.models.rag_document import RAGDocument
    result = db.execute(
        select(func.count(RAGDocument.id)).where(RAGDocument.knowledge_base_id == kb_id)
    )
    return result.scalar() or 0


def create(
    db: Session,
    *,
    name: str,
    collection_name: str,
    scope: str,
    description: str | None = None,
    owner_user_id: str | None = None,
    organization_id: str | None = None,
    is_default: bool = False,
) -> KnowledgeBase:
    kb = KnowledgeBase(
        name=name,
        collection_name=collection_name,
        scope=scope,
        description=description,
        owner_user_id=owner_user_id,
        organization_id=organization_id,
        is_default=is_default,
    )
    db.add(kb)
    db.flush()
    db.refresh(kb)
    return kb


def update(
    db: Session,
    *,
    db_kb: KnowledgeBase,
    name: str | None = None,
    description: str | None = None,
) -> KnowledgeBase:
    if name is not None:
        db_kb.name = name
    if description is not None:
        db_kb.description = description
    db.flush()
    db.refresh(db_kb)
    return db_kb


def delete(db: Session, kb_id: str) -> bool:
    kb = db.get(KnowledgeBase, kb_id)
    if not kb:
        return False
    db.delete(kb)
    db.flush()
    return True

{%- elif cookiecutter.use_mongodb %}
"""Knowledge Base repository (MongoDB async)."""

from app.db.models.knowledge_base import KBScope, KnowledgeBase


async def get_by_id(kb_id: str) -> KnowledgeBase | None:
    return await KnowledgeBase.get(kb_id)


async def get_accessible(
    *,
    user_id: str,
    organization_id: str | None = None,
) -> list[KnowledgeBase]:
    conditions: list[dict] = [
        {"scope": KBScope.PERSONAL.value, "owner_user_id": user_id},
        {"scope": KBScope.APP.value},
    ]
    if organization_id is not None:
        conditions.append({"scope": KBScope.ORG.value, "organization_id": organization_id})
    return await KnowledgeBase.find({"$or": conditions}).sort("created_at").to_list()


async def get_default_for_org(organization_id: str) -> KnowledgeBase | None:
    return await KnowledgeBase.find_one({
        "organization_id": organization_id,
        "scope": KBScope.ORG.value,
        "is_default": True,
    })


async def create(
    *,
    name: str,
    collection_name: str,
    scope: str,
    description: str | None = None,
    owner_user_id: str | None = None,
    organization_id: str | None = None,
    is_default: bool = False,
) -> KnowledgeBase:
    kb = KnowledgeBase(
        name=name,
        collection_name=collection_name,
        scope=scope,
        description=description,
        owner_user_id=owner_user_id,
        organization_id=organization_id,
        is_default=is_default,
    )
    await kb.insert()
    return kb


async def update(
    *,
    db_kb: KnowledgeBase,
    name: str | None = None,
    description: str | None = None,
) -> KnowledgeBase:
    from datetime import UTC, datetime
    if name is not None:
        db_kb.name = name
    if description is not None:
        db_kb.description = description
    db_kb.updated_at = datetime.now(UTC)
    await db_kb.save()
    return db_kb


async def delete(kb_id: str) -> bool:
    kb = await KnowledgeBase.get(kb_id)
    if not kb:
        return False
    await kb.delete()
    return True

{%- endif %}
{%- else %}
"""Knowledge Base repository — not configured."""
{%- endif %}
