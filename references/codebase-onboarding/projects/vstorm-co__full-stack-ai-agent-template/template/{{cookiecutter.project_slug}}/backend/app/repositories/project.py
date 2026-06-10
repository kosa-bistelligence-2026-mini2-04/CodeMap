{%- if cookiecutter.use_pydantic_deep and cookiecutter.use_jwt %}
{%- if cookiecutter.use_postgresql %}
"""Project repository (PostgreSQL async)."""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.project import Project, ProjectMember


# Project Operations


async def get_project_by_id(
    db: AsyncSession,
    project_id: UUID,
) -> Project | None:
    """Get project by ID."""
    return await db.get(Project, project_id)


async def get_projects_for_user(
    db: AsyncSession,
    user_id: UUID,
    *,
    skip: int = 0,
    limit: int = 50,
    include_archived: bool = False,
) -> list[Project]:
    """Get projects where user is owner or member."""
    # Subquery: project IDs where user is a member
    member_project_ids = select(ProjectMember.project_id).where(
        ProjectMember.user_id == user_id
    )
    query = select(Project).where(
        or_(Project.owner_id == user_id, Project.id.in_(member_project_ids))
    )
    if not include_archived:
        query = query.where(Project.archived_at.is_(None))
    query = (
        query.order_by(Project.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(query)
    return list(result.scalars().all())


async def count_projects_for_user(
    db: AsyncSession,
    user_id: UUID,
    *,
    include_archived: bool = False,
) -> int:
    """Count projects accessible to a user."""
    member_project_ids = select(ProjectMember.project_id).where(
        ProjectMember.user_id == user_id
    )
    query = select(func.count(Project.id)).where(
        or_(Project.owner_id == user_id, Project.id.in_(member_project_ids))
    )
    if not include_archived:
        query = query.where(Project.archived_at.is_(None))
    result = await db.execute(query)
    return result.scalar() or 0


async def create_project(
    db: AsyncSession,
    *,
    project_id: UUID | None = None,
    owner_id: UUID,
    name: str,
    description: str | None = None,
    image: str = "python:3.12-slim",
    container_name: str,
    volume_name: str,
) -> Project:
    """Create a new project record."""
    project = Project(
        owner_id=owner_id,
        name=name,
        description=description,
        image=image,
        container_name=container_name,
        volume_name=volume_name,
    )
    if project_id is not None:
        project.id = project_id
    db.add(project)
    await db.flush()
    await db.refresh(project)
    return project


async def update_project(
    db: AsyncSession,
    *,
    db_project: Project,
    update_data: dict[str, Any],
) -> Project:
    """Update project fields."""
    for field, value in update_data.items():
        setattr(db_project, field, value)
    db.add(db_project)
    await db.flush()
    await db.refresh(db_project)
    return db_project


async def archive_project(
    db: AsyncSession,
    project_id: UUID,
) -> Project | None:
    """Soft-delete a project by setting archived_at."""
    project = await get_project_by_id(db, project_id)
    if project:
        project.archived_at = datetime.now(UTC)
        db.add(project)
        await db.flush()
        await db.refresh(project)
    return project


async def delete_project(db: AsyncSession, project_id: UUID) -> bool:
    """Hard-delete a project (cascades to members and conversations)."""
    project = await get_project_by_id(db, project_id)
    if project:
        await db.delete(project)
        await db.flush()
        return True
    return False


# ProjectMember Operations


async def get_project_member(
    db: AsyncSession,
    project_id: UUID,
    user_id: UUID,
) -> ProjectMember | None:
    """Get a specific project member record."""
    result = await db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def get_project_members(
    db: AsyncSession,
    project_id: UUID,
) -> list[ProjectMember]:
    """Get all members of a project."""
    result = await db.execute(
        select(ProjectMember)
        .where(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.created_at.asc())
    )
    return list(result.scalars().all())


async def add_project_member(
    db: AsyncSession,
    *,
    project_id: UUID,
    user_id: UUID,
    role: str = "viewer",
    invited_by: UUID | None = None,
) -> ProjectMember:
    """Add a user to a project."""
    member = ProjectMember(
        project_id=project_id,
        user_id=user_id,
        role=role,
        invited_by=invited_by,
    )
    db.add(member)
    await db.flush()
    await db.refresh(member)
    return member


async def update_member_role(
    db: AsyncSession,
    *,
    db_member: ProjectMember,
    role: str,
) -> ProjectMember:
    """Update a member's role."""
    db_member.role = role
    db.add(db_member)
    await db.flush()
    await db.refresh(db_member)
    return db_member


async def remove_project_member(
    db: AsyncSession,
    project_id: UUID,
    user_id: UUID,
) -> bool:
    """Remove a user from a project."""
    member = await get_project_member(db, project_id, user_id)
    if member:
        await db.delete(member)
        await db.flush()
        return True
    return False


{%- elif cookiecutter.use_sqlite %}
"""Project repository (SQLite sync)."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.db.models.project import Project, ProjectMember


# Project Operations


def get_project_by_id(
    db: Session,
    project_id: str,
) -> Project | None:
    """Get project by ID."""
    return db.get(Project, project_id)


def get_projects_for_user(
    db: Session,
    user_id: str,
    *,
    skip: int = 0,
    limit: int = 50,
    include_archived: bool = False,
) -> list[Project]:
    """Get projects where user is owner or member."""
    member_project_ids = select(ProjectMember.project_id).where(
        ProjectMember.user_id == user_id
    )
    query = select(Project).where(
        or_(Project.owner_id == user_id, Project.id.in_(member_project_ids))
    )
    if not include_archived:
        query = query.where(Project.archived_at.is_(None))
    query = query.order_by(Project.created_at.desc()).offset(skip).limit(limit)
    result = db.execute(query)
    return list(result.scalars().all())


def count_projects_for_user(
    db: Session,
    user_id: str,
    *,
    include_archived: bool = False,
) -> int:
    """Count projects accessible to a user."""
    member_project_ids = select(ProjectMember.project_id).where(
        ProjectMember.user_id == user_id
    )
    query = select(func.count(Project.id)).where(
        or_(Project.owner_id == user_id, Project.id.in_(member_project_ids))
    )
    if not include_archived:
        query = query.where(Project.archived_at.is_(None))
    result = db.execute(query)
    return result.scalar() or 0


def create_project(
    db: Session,
    *,
    project_id: str | None = None,
    owner_id: str,
    name: str,
    description: str | None = None,
    image: str = "python:3.12-slim",
    container_name: str,
    volume_name: str,
) -> Project:
    """Create a new project record."""
    project = Project(
        owner_id=owner_id,
        name=name,
        description=description,
        image=image,
        container_name=container_name,
        volume_name=volume_name,
    )
    if project_id is not None:
        project.id = project_id
    db.add(project)
    db.flush()
    db.refresh(project)
    return project


def update_project(
    db: Session,
    *,
    db_project: Project,
    update_data: dict[str, Any],
) -> Project:
    """Update project fields."""
    for field, value in update_data.items():
        setattr(db_project, field, value)
    db.add(db_project)
    db.flush()
    db.refresh(db_project)
    return db_project


def archive_project(db: Session, project_id: str) -> Project | None:
    """Soft-delete a project by setting archived_at."""
    project = get_project_by_id(db, project_id)
    if project:
        project.archived_at = datetime.now(UTC)
        db.add(project)
        db.flush()
        db.refresh(project)
    return project


def delete_project(db: Session, project_id: str) -> bool:
    """Hard-delete a project."""
    project = get_project_by_id(db, project_id)
    if project:
        db.delete(project)
        db.flush()
        return True
    return False


# ProjectMember Operations


def get_project_member(db: Session, project_id: str, user_id: str) -> ProjectMember | None:
    """Get a specific project member."""
    result = db.execute(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


def get_project_members(db: Session, project_id: str) -> list[ProjectMember]:
    """Get all members of a project."""
    result = db.execute(
        select(ProjectMember)
        .where(ProjectMember.project_id == project_id)
        .order_by(ProjectMember.created_at.asc())
    )
    return list(result.scalars().all())


def add_project_member(
    db: Session,
    *,
    project_id: str,
    user_id: str,
    role: str = "viewer",
    invited_by: str | None = None,
) -> ProjectMember:
    """Add a user to a project."""
    member = ProjectMember(
        project_id=project_id,
        user_id=user_id,
        role=role,
        invited_by=invited_by,
    )
    db.add(member)
    db.flush()
    db.refresh(member)
    return member


def update_member_role(
    db: Session,
    *,
    db_member: ProjectMember,
    role: str,
) -> ProjectMember:
    """Update a member's role."""
    db_member.role = role
    db.add(db_member)
    db.flush()
    db.refresh(db_member)
    return db_member


def remove_project_member(db: Session, project_id: str, user_id: str) -> bool:
    """Remove a user from a project."""
    member = get_project_member(db, project_id, user_id)
    if member:
        db.delete(member)
        db.flush()
        return True
    return False


{%- elif cookiecutter.use_mongodb %}
"""Project repository (MongoDB)."""

from datetime import UTC, datetime
from typing import Any

from beanie import PydanticObjectId

from app.db.models.project import Project, ProjectMember


# Project Operations


async def get_project_by_id(project_id: str) -> Project | None:
    """Get project by ID."""
    return await Project.get(project_id)


async def get_projects_for_user(
    user_id: str,
    *,
    skip: int = 0,
    limit: int = 50,
    include_archived: bool = False,
) -> list[Project]:
    """Get projects where user is owner or member of."""
    # Get member project IDs first
    member_entries = await ProjectMember.find(
        ProjectMember.user_id == user_id
    ).to_list()
    # Convert string IDs to PydanticObjectId so MongoDB _id comparison works
    member_oids = [
        PydanticObjectId(m.project_id)
        for m in member_entries
        if m.project_id
    ]

    query_filter: dict[str, Any] = {
        "$or": [{"owner_id": user_id}, {"_id": {"$in": member_oids}}]
    }
    if not include_archived:
        query_filter["archived_at"] = None

    return (
        await Project.find(query_filter)
        .sort("-created_at")
        .skip(skip)
        .limit(limit)
        .to_list()
    )


async def count_projects_for_user(
    user_id: str,
    *,
    include_archived: bool = False,
) -> int:
    """Count projects accessible to a user."""
    member_entries = await ProjectMember.find(
        ProjectMember.user_id == user_id
    ).to_list()
    member_oids = [
        PydanticObjectId(m.project_id)
        for m in member_entries
        if m.project_id
    ]

    query_filter: dict[str, Any] = {
        "$or": [{"owner_id": user_id}, {"_id": {"$in": member_oids}}]
    }
    if not include_archived:
        query_filter["archived_at"] = None
    return await Project.find(query_filter).count()


async def create_project(
    *,
    owner_id: str,
    name: str,
    description: str | None = None,
    image: str = "python:3.12-slim",
    container_name: str,
    volume_name: str,
) -> Project:
    """Create a new project."""
    project = Project(
        owner_id=owner_id,
        name=name,
        description=description,
        image=image,
        container_name=container_name,
        volume_name=volume_name,
    )
    await project.insert()
    return project


async def update_project(
    *,
    db_project: Project,
    update_data: dict[str, Any],
) -> Project:
    """Update project fields."""
    for field, value in update_data.items():
        setattr(db_project, field, value)
    db_project.updated_at = datetime.now(UTC)
    await db_project.save()
    return db_project


async def archive_project(project_id: str) -> Project | None:
    """Soft-delete a project."""
    project = await get_project_by_id(project_id)
    if project:
        project.archived_at = datetime.now(UTC)
        project.updated_at = datetime.now(UTC)
        await project.save()
    return project


async def delete_project(project_id: str) -> bool:
    """Hard-delete a project."""
    project = await get_project_by_id(project_id)
    if project:
        await ProjectMember.find(ProjectMember.project_id == str(project.id)).delete()
        await project.delete()
        return True
    return False


# ProjectMember Operations


async def get_project_member(project_id: str, user_id: str) -> ProjectMember | None:
    """Get a specific project member."""
    return await ProjectMember.find_one(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
    )


async def get_project_members(project_id: str) -> list[ProjectMember]:
    """Get all members of a project."""
    return (
        await ProjectMember.find(ProjectMember.project_id == project_id)
        .sort("created_at")
        .to_list()
    )


async def add_project_member(
    *,
    project_id: str,
    user_id: str,
    role: str = "viewer",
    invited_by: str | None = None,
) -> ProjectMember:
    """Add a user to a project."""
    member = ProjectMember(
        project_id=project_id,
        user_id=user_id,
        role=role,
        invited_by=invited_by,
    )
    await member.insert()
    return member


async def update_member_role(
    *,
    db_member: ProjectMember,
    role: str,
) -> ProjectMember:
    """Update a member's role."""
    db_member.role = role
    await db_member.save()
    return db_member


async def remove_project_member(project_id: str, user_id: str) -> bool:
    """Remove a user from a project."""
    member = await get_project_member(project_id, user_id)
    if member:
        await member.delete()
        return True
    return False


{%- else %}
"""Project repository - no database configured."""
{%- endif %}
{%- else %}
"""Project repository - requires use_pydantic_deep and use_jwt."""
{%- endif %}
