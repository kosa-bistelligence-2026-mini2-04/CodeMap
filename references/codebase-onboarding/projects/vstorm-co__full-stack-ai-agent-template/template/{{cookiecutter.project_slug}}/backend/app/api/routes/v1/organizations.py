{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""Organization CRUD routes."""

{%- if cookiecutter.use_postgresql %}
import contextlib
from pathlib import Path
{%- endif %}
from typing import Any
{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}

{%- if cookiecutter.use_postgresql %}
from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
{%- else %}
from fastapi import APIRouter, status
{%- endif %}

from app.api.deps import CurrentUser, OrganizationSvc
{%- if cookiecutter.use_postgresql %}
from app.db.models.organization import OrgRole
{%- endif %}
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationList,
    OrganizationRead,
    OrganizationUpdate,
)
{%- if cookiecutter.use_postgresql %}
from app.services.file_storage import get_file_storage

ALLOWED_AVATAR_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_AVATAR_BYTES = 2 * 1024 * 1024
{%- endif %}

router = APIRouter()


@router.get("", response_model=OrganizationList)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def list_organizations(
    service: OrganizationSvc,
    user: CurrentUser,
) -> Any:
{%- else %}
def list_organizations(
    service: OrganizationSvc,
    user: CurrentUser,
) -> Any:
{%- endif %}
    """List all organizations the current user belongs to."""
{%- if cookiecutter.use_postgresql %}
    rows = await service.list_for_user(user.id)
{%- elif cookiecutter.use_sqlite %}
    rows = service.list_for_user(str(user.id))
{%- else %}
    rows = await service.list_for_user(str(user.id))
{%- endif %}
    items = [
        OrganizationRead(
            id=row["org"].id,
            name=row["org"].name,
            slug=row["org"].slug,
            is_personal=row["org"].is_personal,
            avatar_url=row["org"].avatar_url,
            member_count=row["member_count"],
            role=row["role"],
            created_at=row["org"].created_at,
            updated_at=row["org"].updated_at,
{%- if cookiecutter.enable_billing %}
            subscription_tier=getattr(row["org"], "subscription_tier", "free"),
            credits_balance=getattr(row["org"], "credits_balance", 0),
{%- endif %}
        )
        for row in rows
    ]
    return OrganizationList(items=items, total=len(items))


@router.post("", response_model=OrganizationRead, status_code=status.HTTP_201_CREATED)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def create_organization(
    data: OrganizationCreate,
    service: OrganizationSvc,
    user: CurrentUser,
) -> Any:
{%- else %}
def create_organization(
    data: OrganizationCreate,
    service: OrganizationSvc,
    user: CurrentUser,
) -> Any:
{%- endif %}
    """Create a new organization. The requesting user becomes Owner."""
{%- if cookiecutter.use_postgresql %}
    org = await service.create(data, owner_id=user.id)
    rows = await service.list_for_user(user.id)
    member_count = next((r["member_count"] for r in rows if r["org"].id == org.id), 1)
    role = next((r["role"] for r in rows if r["org"].id == org.id), "owner")
{%- elif cookiecutter.use_sqlite %}
    org = service.create(data, owner_id=str(user.id))
    rows = service.list_for_user(str(user.id))
    member_count = next((r["member_count"] for r in rows if r["org"].id == org.id), 1)
    role = next((r["role"] for r in rows if r["org"].id == org.id), "owner")
{%- else %}
    org = await service.create(data, owner_id=str(user.id))
    rows = await service.list_for_user(str(user.id))
    member_count = next((r["member_count"] for r in rows if str(r["org"].id) == str(org.id)), 1)
    role = next((r["role"] for r in rows if str(r["org"].id) == str(org.id)), "owner")
{%- endif %}
    return OrganizationRead(
        id=org.id,
        name=org.name,
        slug=org.slug,
        is_personal=org.is_personal,
        avatar_url=org.avatar_url,
        member_count=member_count,
        role=role,
        created_at=org.created_at,
        updated_at=org.updated_at,
{%- if cookiecutter.enable_billing %}
        subscription_tier=getattr(org, "subscription_tier", "free"),
        credits_balance=getattr(org, "credits_balance", 0),
{%- endif %}
    )


@router.get("/{org_id}", response_model=OrganizationRead)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def get_organization(
{%- if cookiecutter.use_postgresql %}
    org_id: UUID,
{%- else %}
    org_id: str,
{%- endif %}
    service: OrganizationSvc,
    user: CurrentUser,
) -> Any:
{%- else %}
def get_organization(
    org_id: str,
    service: OrganizationSvc,
    user: CurrentUser,
) -> Any:
{%- endif %}
    """Get a single organization the current user is a member of."""
{%- if cookiecutter.use_postgresql %}
    org, membership = await service.get_for_user(org_id, user.id)
    from app.repositories import organization_repo
    from app.db.session import get_db_context
    # member_count is fetched inline via get_for_user flow — use service
    rows = await service.list_for_user(user.id)
    member_count = next((r["member_count"] for r in rows if r["org"].id == org.id), 0)
{%- elif cookiecutter.use_sqlite %}
    org, membership = service.get_for_user(org_id, str(user.id))
    rows = service.list_for_user(str(user.id))
    member_count = next((r["member_count"] for r in rows if r["org"].id == org.id), 0)
{%- else %}
    org, membership = await service.get_for_user(org_id, str(user.id))
    rows = await service.list_for_user(str(user.id))
    member_count = next((r["member_count"] for r in rows if str(r["org"].id) == str(org.id)), 0)
{%- endif %}
    return OrganizationRead(
        id=org.id,
        name=org.name,
        slug=org.slug,
        is_personal=org.is_personal,
        avatar_url=org.avatar_url,
        member_count=member_count,
        role=membership.role,
        created_at=org.created_at,
        updated_at=org.updated_at,
{%- if cookiecutter.enable_billing %}
        subscription_tier=getattr(org, "subscription_tier", "free"),
        credits_balance=getattr(org, "credits_balance", 0),
{%- endif %}
    )


@router.patch("/{org_id}", response_model=OrganizationRead)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def update_organization(
{%- if cookiecutter.use_postgresql %}
    org_id: UUID,
{%- else %}
    org_id: str,
{%- endif %}
    data: OrganizationUpdate,
    service: OrganizationSvc,
    user: CurrentUser,
) -> Any:
{%- else %}
def update_organization(
    org_id: str,
    data: OrganizationUpdate,
    service: OrganizationSvc,
    user: CurrentUser,
) -> Any:
{%- endif %}
    """Update organization name or avatar. Requires Admin or Owner role."""
{%- if cookiecutter.use_postgresql %}
    org = await service.update(org_id, data, requester_id=user.id)
    rows = await service.list_for_user(user.id)
    member_count = next((r["member_count"] for r in rows if r["org"].id == org.id), 0)
    role = next((r["role"] for r in rows if r["org"].id == org.id), "member")
{%- elif cookiecutter.use_sqlite %}
    org = service.update(org_id, data, requester_id=str(user.id))
    rows = service.list_for_user(str(user.id))
    member_count = next((r["member_count"] for r in rows if r["org"].id == org.id), 0)
    role = next((r["role"] for r in rows if r["org"].id == org.id), "member")
{%- else %}
    org = await service.update(org_id, data, requester_id=str(user.id))
    rows = await service.list_for_user(str(user.id))
    member_count = next((r["member_count"] for r in rows if str(r["org"].id) == str(org.id)), 0)
    role = next((r["role"] for r in rows if str(r["org"].id) == str(org.id)), "member")
{%- endif %}
    return OrganizationRead(
        id=org.id,
        name=org.name,
        slug=org.slug,
        is_personal=org.is_personal,
        avatar_url=org.avatar_url,
        member_count=member_count,
        role=role,
        created_at=org.created_at,
        updated_at=org.updated_at,
{%- if cookiecutter.enable_billing %}
        subscription_tier=getattr(org, "subscription_tier", "free"),
        credits_balance=getattr(org, "credits_balance", 0),
{%- endif %}
    )


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def delete_organization(
{%- if cookiecutter.use_postgresql %}
    org_id: UUID,
{%- else %}
    org_id: str,
{%- endif %}
    service: OrganizationSvc,
    user: CurrentUser,
) -> None:
{%- else %}
def delete_organization(
    org_id: str,
    service: OrganizationSvc,
    user: CurrentUser,
) -> None:
{%- endif %}
    """Delete an organization. Requires Owner role. Personal orgs cannot be deleted."""
{%- if cookiecutter.use_postgresql %}
    await service.delete(org_id, requester_id=user.id)
{%- elif cookiecutter.use_sqlite %}
    service.delete(org_id, requester_id=str(user.id))
{%- else %}
    await service.delete(org_id, requester_id=str(user.id))
{%- endif %}

{%- if cookiecutter.use_postgresql %}


@router.post("/{org_id}/avatar", response_model=OrganizationRead)
async def upload_organization_avatar(
    org_id: UUID,
    service: OrganizationSvc,
    user: CurrentUser,
    file: UploadFile = File(...),
) -> Any:
    """Upload or replace the organization avatar. Requires Admin or Owner role."""
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(
            status_code=400, detail="Only JPEG, PNG, WebP, and GIF images are allowed"
        )
    data = await file.read()
    if len(data) > MAX_AVATAR_BYTES:
        raise HTTPException(status_code=400, detail="Avatar image too large. Maximum 2MB.")

    # Authorization is enforced by service.update — but we replicate the check
    # here so we don't write a file the user can't actually attach.
    org, membership = await service.get_for_user(org_id, user.id)
    if membership.role not in (OrgRole.OWNER.value, OrgRole.ADMIN.value):
        raise HTTPException(status_code=403, detail="Only Owner or Admin can update the org")

    storage = get_file_storage()
    if org.avatar_url:
        with contextlib.suppress(Exception):
            await storage.delete(org.avatar_url)
    storage_path = await storage.save(
        f"avatars/orgs/{org_id}", file.filename or "avatar.jpg", data
    )
    updated = await service.update(
        org_id, OrganizationUpdate(avatar_url=storage_path), requester_id=user.id
    )
    rows = await service.list_for_user(user.id)
    member_count = next((r["member_count"] for r in rows if r["org"].id == updated.id), 0)
    role = next((r["role"] for r in rows if r["org"].id == updated.id), "member")
    return OrganizationRead(
        id=updated.id,
        name=updated.name,
        slug=updated.slug,
        is_personal=updated.is_personal,
        avatar_url=updated.avatar_url,
        member_count=member_count,
        role=role,
        created_at=updated.created_at,
        updated_at=updated.updated_at,
        subscription_tier=getattr(updated, "subscription_tier", "free"),
        credits_balance=getattr(updated, "credits_balance", 0),
    )


@router.get("/{org_id}/avatar")
async def get_organization_avatar(
    org_id: UUID,
    service: OrganizationSvc,
    user: CurrentUser,
) -> Any:
    """Stream the organization avatar image. Membership is required to view."""
    org, _ = await service.get_for_user(org_id, user.id)
    if not org.avatar_url:
        raise HTTPException(status_code=404, detail="No avatar set")
    storage = get_file_storage()
    file_path = storage.get_full_path(org.avatar_url)
    if not file_path or not Path(file_path).exists():
        raise HTTPException(status_code=404, detail="Avatar file missing")
    return FileResponse(path=file_path, media_type="image/jpeg")
{%- endif %}


{%- else %}
"""Organization routes — not configured (enable_teams=false or no JWT)."""
{%- endif %}
