{%- if cookiecutter.enable_teams and cookiecutter.use_jwt %}
"""Invitation management routes.

org_router  → mounted at /orgs  → /orgs/{org_id}/invitations (CRUD)
token_router → mounted at root  → /invitations/{token}/accept|DELETE
"""

from typing import Any
{%- if cookiecutter.use_postgresql %}
from uuid import UUID
{%- endif %}

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, InvitationSvc
from app.schemas.organization import (
    InvitationCreate,
    InvitationList,
    InvitationRead,
)

# Routes nested under /orgs/{org_id}/invitations
org_router = APIRouter()

# Routes for token-based operations: /invitations/{token}/*
token_router = APIRouter()


@org_router.post("/{org_id}/invitations", response_model=InvitationRead, status_code=status.HTTP_201_CREATED)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def create_invitation(
{%- if cookiecutter.use_postgresql %}
    org_id: UUID,
{%- else %}
    org_id: str,
{%- endif %}
    data: InvitationCreate,
    service: InvitationSvc,
    user: CurrentUser,
) -> Any:
{%- else %}
def create_invitation(
    org_id: str,
    data: InvitationCreate,
    service: InvitationSvc,
    user: CurrentUser,
) -> Any:
{%- endif %}
    """Invite a user to the organization by email. Requires Owner or Admin."""
{%- if cookiecutter.use_postgresql %}
    invite = await service.invite(org_id, data.email, data.role, requester_id=user.id)
{%- elif cookiecutter.use_sqlite %}
    invite = service.invite(org_id, data.email, data.role, requester_id=str(user.id))
{%- else %}
    invite = await service.invite(org_id, data.email, data.role, requester_id=str(user.id))
{%- endif %}
    return InvitationRead(
        id=invite.id,
        organization_id=invite.organization_id,
        email=invite.email,
        role=invite.role,
        status=invite.status,
        token=invite.token,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
    )


@org_router.get("/{org_id}/invitations", response_model=InvitationList)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def list_invitations(
{%- if cookiecutter.use_postgresql %}
    org_id: UUID,
{%- else %}
    org_id: str,
{%- endif %}
    service: InvitationSvc,
    user: CurrentUser,
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return"),
) -> Any:
{%- else %}
def list_invitations(
    org_id: str,
    service: InvitationSvc,
    user: CurrentUser,
    status_filter: str | None = Query(None, alias="status", description="Filter by status"),
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return"),
) -> Any:
{%- endif %}
    """List invitations for an organization. Requires Owner or Admin."""
{%- if cookiecutter.use_postgresql %}
    invites = await service.list_for_org(
        org_id, user.id, status=status_filter, skip=skip, limit=limit
    )
{%- elif cookiecutter.use_sqlite %}
    invites = service.list_for_org(
        org_id, str(user.id), status=status_filter, skip=skip, limit=limit
    )
{%- else %}
    invites = await service.list_for_org(
        org_id, str(user.id), status=status_filter, skip=skip, limit=limit
    )
{%- endif %}
    items = [
        InvitationRead(
            id=inv.id,
            organization_id=inv.organization_id,
            email=inv.email,
            role=inv.role,
            status=inv.status,
            token=inv.token,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
        )
        for inv in invites
    ]
    return InvitationList(items=items, total=len(items))


@token_router.post("/invitations/{token}/accept", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def accept_invitation(
    token: str,
    service: InvitationSvc,
    user: CurrentUser,
) -> None:
{%- else %}
def accept_invitation(
    token: str,
    service: InvitationSvc,
    user: CurrentUser,
) -> None:
{%- endif %}
    """Accept an invitation token. Adds the current user to the organization."""
{%- if cookiecutter.use_postgresql %}
    await service.accept(token, accepting_user_id=user.id)
{%- elif cookiecutter.use_sqlite %}
    service.accept(token, accepting_user_id=str(user.id))
{%- else %}
    await service.accept(token, accepting_user_id=str(user.id))
{%- endif %}


@token_router.delete("/invitations/{token}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
{%- if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
async def revoke_invitation(
    token: str,
    service: InvitationSvc,
    user: CurrentUser,
) -> None:
{%- else %}
def revoke_invitation(
    token: str,
    service: InvitationSvc,
    user: CurrentUser,
) -> None:
{%- endif %}
    """Revoke a pending invitation. Owner/Admin of the org, or the invitee themselves."""
{%- if cookiecutter.use_postgresql %}
    await service.revoke(token, requester_id=user.id)
{%- elif cookiecutter.use_sqlite %}
    service.revoke(token, requester_id=str(user.id))
{%- else %}
    await service.revoke(token, requester_id=str(user.id))
{%- endif %}


{%- else %}
"""Invitation routes — not configured (enable_teams=false or no JWT)."""

from fastapi import APIRouter

org_router = APIRouter()
token_router = APIRouter()
{%- endif %}
