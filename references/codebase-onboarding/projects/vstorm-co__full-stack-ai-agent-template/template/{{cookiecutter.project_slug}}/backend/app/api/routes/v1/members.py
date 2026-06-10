{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""Member management routes (nested under /orgs/{org_id}/members)."""

from typing import Any
{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, MemberSvc
from app.schemas.organization import (
    OrganizationMemberList,
    OrganizationMemberRead,
    OrganizationMemberUpdate,
    TransferOwnershipRequest,
)

router = APIRouter()


@router.get("/{org_id}/members", response_model=OrganizationMemberList)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def list_members(
{%- if cookiecutter.use_postgresql %}
    org_id: UUID,
{%- else %}
    org_id: str,
{%- endif %}
    service: MemberSvc,
    user: CurrentUser,
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return"),
) -> Any:
{%- else %}
def list_members(
    org_id: str,
    service: MemberSvc,
    user: CurrentUser,
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return"),
) -> Any:
{%- endif %}
    """List members of an organization. Any member may call this."""
{%- if cookiecutter.use_postgresql %}
    rows, total = await service.list_for_org(org_id, user.id, skip=skip, limit=limit)
{%- elif cookiecutter.use_sqlite %}
    rows, total = service.list_for_org(org_id, str(user.id), skip=skip, limit=limit)
{%- else %}
    rows, total = await service.list_for_org(org_id, str(user.id), skip=skip, limit=limit)
{%- endif %}
    items = [
        OrganizationMemberRead(
            id=m.id,
            organization_id=m.organization_id,
            user_id=m.user_id,
            role=m.role,
            email=email,
            full_name=full_name,
            avatar_url=avatar_url,
            joined_at=m.joined_at,
        )
        for m, email, full_name, avatar_url in rows
    ]
    return OrganizationMemberList(items=items, total=total)


@router.patch("/{org_id}/members/{target_user_id}", response_model=OrganizationMemberRead)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def update_member_role(
{%- if cookiecutter.use_postgresql %}
    org_id: UUID,
    target_user_id: UUID,
{%- else %}
    org_id: str,
    target_user_id: str,
{%- endif %}
    data: OrganizationMemberUpdate,
    service: MemberSvc,
    user: CurrentUser,
) -> Any:
{%- else %}
def update_member_role(
    org_id: str,
    target_user_id: str,
    data: OrganizationMemberUpdate,
    service: MemberSvc,
    user: CurrentUser,
) -> Any:
{%- endif %}
    """Change a member's role. Requires Owner or Admin."""
{%- if cookiecutter.use_postgresql %}
    member, email, full_name, avatar_url = await service.change_role(org_id, target_user_id, data.role, requester_id=user.id)
{%- elif cookiecutter.use_sqlite %}
    member, email, full_name, avatar_url = service.change_role(org_id, target_user_id, data.role, requester_id=str(user.id))
{%- else %}
    member, email, full_name, avatar_url = await service.change_role(org_id, target_user_id, data.role, requester_id=str(user.id))
{%- endif %}
    return OrganizationMemberRead(
        id=member.id,
        organization_id=member.organization_id,
        user_id=member.user_id,
        role=member.role,
        email=email,
        full_name=full_name,
        avatar_url=avatar_url,
        joined_at=member.joined_at,
    )


@router.delete(
    "/{org_id}/members/{target_user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def remove_member(
{%- if cookiecutter.use_postgresql %}
    org_id: UUID,
    target_user_id: UUID,
{%- else %}
    org_id: str,
    target_user_id: str,
{%- endif %}
    service: MemberSvc,
    user: CurrentUser,
) -> None:
{%- else %}
def remove_member(
    org_id: str,
    target_user_id: str,
    service: MemberSvc,
    user: CurrentUser,
) -> None:
{%- endif %}
    """Remove a member from the organization. Requires Owner or Admin."""
{%- if cookiecutter.use_postgresql %}
    await service.remove(org_id, target_user_id, requester_id=user.id)
{%- elif cookiecutter.use_sqlite %}
    service.remove(org_id, target_user_id, requester_id=str(user.id))
{%- else %}
    await service.remove(org_id, target_user_id, requester_id=str(user.id))
{%- endif %}


@router.post("/{org_id}/leave", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def leave_organization(
{%- if cookiecutter.use_postgresql %}
    org_id: UUID,
{%- else %}
    org_id: str,
{%- endif %}
    service: MemberSvc,
    user: CurrentUser,
) -> None:
{%- else %}
def leave_organization(
    org_id: str,
    service: MemberSvc,
    user: CurrentUser,
) -> None:
{%- endif %}
    """Leave an organization. Owner must transfer ownership first if others remain."""
{%- if cookiecutter.use_postgresql %}
    await service.leave(org_id, requester_id=user.id)
{%- elif cookiecutter.use_sqlite %}
    service.leave(org_id, requester_id=str(user.id))
{%- else %}
    await service.leave(org_id, requester_id=str(user.id))
{%- endif %}


@router.post("/{org_id}/transfer-ownership", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def transfer_ownership(
{%- if cookiecutter.use_postgresql %}
    org_id: UUID,
{%- else %}
    org_id: str,
{%- endif %}
    data: TransferOwnershipRequest,
    service: MemberSvc,
    user: CurrentUser,
) -> None:
{%- else %}
def transfer_ownership(
    org_id: str,
    data: TransferOwnershipRequest,
    service: MemberSvc,
    user: CurrentUser,
) -> None:
{%- endif %}
    """Transfer Owner role to another member. Caller becomes Admin."""
{%- if cookiecutter.use_postgresql %}
    await service.transfer_ownership(org_id, data.new_owner_user_id, requester_id=user.id)
{%- elif cookiecutter.use_sqlite %}
    service.transfer_ownership(org_id, data.new_owner_user_id, requester_id=str(user.id))
{%- else %}
    await service.transfer_ownership(org_id, data.new_owner_user_id, requester_id=str(user.id))
{%- endif %}


{%- else %}
"""Member routes — not configured (enable_teams=false or no JWT)."""
{%- endif %}
