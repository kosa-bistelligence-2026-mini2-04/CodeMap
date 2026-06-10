{%- if cookiecutter.use_postgresql %}
"""Invitation service (PostgreSQL async).

Business logic for creating, listing, accepting, and revoking org invitations.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    AuthorizationError,
    BadRequestError,
    NotFoundError,
    PaymentRequiredError,
)
from app.db.models.organization import InvitationStatus, OrgRole
from app.repositories import invitation_repo, member_repo, organization_repo, user_repo
{%- if cookiecutter.enable_email %}
from app.services.email.service import get_email_service
{%- endif %}

logger = logging.getLogger(__name__)

_ADMIN_INVITABLE_ROLES = {OrgRole.MEMBER.value, OrgRole.VIEWER.value}


class InvitationService:
    """Service for organization invitation management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def invite(
        self,
        organization_id: UUID,
        email: str,
        role: str,
        requester_id: UUID,
    ):
        """Send an invitation to join an org.

        Rules:
        - Only OWNER or ADMIN may invite.
        - ADMIN can only invite MEMBER or VIEWER.
        - Cannot invite someone already a member.
        - Cannot duplicate a pending invitation for the same email.
        """
        requester = await member_repo.get(
            self.db, organization_id=organization_id, user_id=requester_id
        )
        if not requester or requester.role not in (OrgRole.OWNER.value, OrgRole.ADMIN.value):
            raise AuthorizationError(message="Only Owner or Admin can invite members")

        if requester.role == OrgRole.ADMIN.value and role not in _ADMIN_INVITABLE_ROLES:
            raise AuthorizationError(message="Admin can only invite as Member or Viewer")

        normalized_email = email.lower()

        # Check if already a member (by email via user lookup)
        existing_user = await user_repo.get_by_email(self.db, normalized_email)
        if existing_user:
            existing_membership = await member_repo.get(
                self.db, organization_id=organization_id, user_id=existing_user.id
            )
            if existing_membership:
                raise AlreadyExistsError(
                    message="User is already a member of this organization",
                    details={"email": normalized_email},
                )

        # Duplicate pending invitation check
        pending = await invitation_repo.get_pending_for_org_email(
            self.db, organization_id=organization_id, email=normalized_email
        )
        if pending:
            raise AlreadyExistsError(
                message="A pending invitation already exists for this email",
                details={"email": normalized_email},
            )

        invite = await invitation_repo.create(
            self.db,
            organization_id=organization_id,
            email=normalized_email,
            role=role,
            invited_by_user_id=requester_id,
        )
        logger.info(
            "Invitation created for %s to org %s (role=%s) by user %s",
            normalized_email,
            organization_id,
            role,
            requester_id,
        )
{%- if cookiecutter.enable_email %}
        try:
            org = await organization_repo.get_by_id(self.db, organization_id)
            requester_user = await user_repo.get_by_id(self.db, requester_id)
            frontend = settings.FRONTEND_URL.rstrip("/")
            accept_url = f"{frontend}/invitations/{invite.token}"
            await get_email_service().send_invitation(
                to=normalized_email,
                inviter_name=(requester_user.full_name or requester_user.email)
                if requester_user
                else "A team member",
                org_name=org.name if org else "the organization",
                accept_url=accept_url,
            )
        except Exception:
            logger.exception("email_invitation_failed")
{%- endif %}
        return invite

    async def list_for_org(
        self,
        organization_id: UUID,
        requester_id: UUID,
        *,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ):
        """List invitations. Only OWNER or ADMIN may list."""
        requester = await member_repo.get(
            self.db, organization_id=organization_id, user_id=requester_id
        )
        if not requester or requester.role not in (OrgRole.OWNER.value, OrgRole.ADMIN.value):
            raise AuthorizationError(message="Only Owner or Admin can view invitations")

        return await invitation_repo.list_for_org(
            self.db, organization_id, status=status, skip=skip, limit=limit
        )

    async def accept(self, token: str, accepting_user_id: UUID):
        """Accept an invitation by token.

        Creates the OrganizationMember record. Token must be PENDING and not expired.
        """
        invite = await invitation_repo.get_by_token(self.db, token)
        if not invite:
            raise NotFoundError(message="Invitation not found or already used")

        if invite.status != InvitationStatus.PENDING.value:
            raise BadRequestError(
                message="Invitation is no longer valid",
                details={"status": invite.status},
            )

        if invite.expires_at and invite.expires_at < datetime.now(UTC):
            await invitation_repo.revoke(self.db, invite)
            raise BadRequestError(message="Invitation has expired")

        # The token is bound to a specific email — only that user may accept.
        accepting_user = await user_repo.get_by_id(self.db, accepting_user_id)
        if not accepting_user or accepting_user.email.lower() != invite.email:
            raise AuthenticationError(
                message="This invitation was sent to a different email address."
            )

        # Check not already a member
        existing = await member_repo.get(
            self.db, organization_id=invite.organization_id, user_id=accepting_user_id
        )
        if existing:
            raise AlreadyExistsError(
                message="You are already a member of this organization",
                details={"org_id": str(invite.organization_id)},
            )
        # Enforce seat limit before admitting a new member
        org = await organization_repo.get_by_id(self.db, invite.organization_id)
        seats_limit = getattr(org, "seats_limit", None) if org is not None else None
        if seats_limit is not None:
            current_count = await member_repo.count_for_org(self.db, invite.organization_id)
            if current_count >= seats_limit:
                raise PaymentRequiredError(
                    message="Seat limit reached — upgrade your plan to add more members",
                    details={"seats_limit": seats_limit, "current": current_count},
                )
        await member_repo.create(
            self.db,
            organization_id=invite.organization_id,
            user_id=accepting_user_id,
            role=invite.role,
        )
        await invitation_repo.accept(self.db, invite, accepted_by_user_id=accepting_user_id)
        logger.info(
            "Invitation %s accepted by user %s (org %s)",
            invite.id,
            accepting_user_id,
            invite.organization_id,
        )
        return invite

    async def revoke(self, token: str, requester_id: UUID):
        """Revoke a pending invitation.

        OWNER or ADMIN may revoke. Invitee can cancel their own invitation via this too.
        """
        invite = await invitation_repo.get_by_token(self.db, token)
        if not invite:
            raise NotFoundError(message="Invitation not found")

        if invite.status != InvitationStatus.PENDING.value:
            raise BadRequestError(
                message="Only pending invitations can be revoked",
                details={"status": invite.status},
            )

        requester = await member_repo.get(
            self.db, organization_id=invite.organization_id, user_id=requester_id
        )
        # Allow the invitee (non-member) to cancel their own invite, or admin/owner of the org
        accepting_user = await user_repo.get_by_id(self.db, requester_id)
        is_own_invite = accepting_user and accepting_user.email.lower() == invite.email

        if not is_own_invite and (
            not requester or requester.role not in (OrgRole.OWNER.value, OrgRole.ADMIN.value)
        ):
            raise AuthorizationError(message="Only Owner or Admin can revoke invitations")

        await invitation_repo.revoke(self.db, invite)
        return invite


{%- elif cookiecutter.use_sqlite %}
"""Invitation service (SQLite sync).

Business logic for creating, listing, accepting, and revoking org invitations.
"""

import logging
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    AuthorizationError,
    BadRequestError,
    NotFoundError,
    PaymentRequiredError,
)
from app.db.models.organization import InvitationStatus, OrgRole
from app.repositories import invitation_repo, member_repo, organization_repo, user_repo
{%- if cookiecutter.enable_email %}
from app.services.email.service import get_email_service
{%- endif %}

logger = logging.getLogger(__name__)

_ADMIN_INVITABLE_ROLES = {OrgRole.MEMBER.value, OrgRole.VIEWER.value}


class InvitationService:
    """Service for organization invitation management."""

    def __init__(self, db: Session):
        self.db = db

    def invite(self, organization_id: str, email: str, role: str, requester_id: str):
        """Send an invitation to join an org."""
        requester = member_repo.get(
            self.db, organization_id=organization_id, user_id=requester_id
        )
        if not requester or requester.role not in (OrgRole.OWNER.value, OrgRole.ADMIN.value):
            raise AuthorizationError(message="Only Owner or Admin can invite members")

        if requester.role == OrgRole.ADMIN.value and role not in _ADMIN_INVITABLE_ROLES:
            raise AuthorizationError(message="Admin can only invite as Member or Viewer")

        normalized_email = email.lower()

        existing_user = user_repo.get_by_email(self.db, normalized_email)
        if existing_user:
            existing_membership = member_repo.get(
                self.db, organization_id=organization_id, user_id=existing_user.id
            )
            if existing_membership:
                raise AlreadyExistsError(
                    message="User is already a member of this organization",
                    details={"email": normalized_email},
                )

        pending = invitation_repo.get_pending_for_org_email(
            self.db, organization_id=organization_id, email=normalized_email
        )
        if pending:
            raise AlreadyExistsError(
                message="A pending invitation already exists for this email",
                details={"email": normalized_email},
            )

        invite = invitation_repo.create(
            self.db,
            organization_id=organization_id,
            email=normalized_email,
            role=role,
            invited_by_user_id=requester_id,
        )
        logger.info(
            "Invitation created for %s to org %s (role=%s) by user %s",
            normalized_email, organization_id, role, requester_id,
        )
        return invite

    def list_for_org(
        self,
        organization_id: str,
        requester_id: str,
        *,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ):
        """List invitations. Only OWNER or ADMIN may list."""
        requester = member_repo.get(
            self.db, organization_id=organization_id, user_id=requester_id
        )
        if not requester or requester.role not in (OrgRole.OWNER.value, OrgRole.ADMIN.value):
            raise AuthorizationError(message="Only Owner or Admin can view invitations")

        return invitation_repo.list_for_org(
            self.db, organization_id, status=status, skip=skip, limit=limit
        )

    def accept(self, token: str, accepting_user_id: str):
        """Accept an invitation by token."""
        invite = invitation_repo.get_by_token(self.db, token)
        if not invite:
            raise NotFoundError(message="Invitation not found or already used")

        if invite.status != InvitationStatus.PENDING.value:
            raise BadRequestError(
                message="Invitation is no longer valid",
                details={"status": invite.status},
            )

        if invite.expires_at and invite.expires_at < datetime.now(UTC):
            invitation_repo.revoke(self.db, invite)
            raise BadRequestError(message="Invitation has expired")

        accepting_user = user_repo.get_by_id(self.db, accepting_user_id)
        if not accepting_user or accepting_user.email.lower() != invite.email:
            raise AuthenticationError(
                message="This invitation was sent to a different email address."
            )

        existing = member_repo.get(
            self.db, organization_id=invite.organization_id, user_id=accepting_user_id
        )
        if existing:
            raise AlreadyExistsError(
                message="You are already a member of this organization",
                details={"org_id": str(invite.organization_id)},
            )

        org = organization_repo.get_by_id(self.db, invite.organization_id)
        seats_limit = getattr(org, "seats_limit", None) if org is not None else None
        if seats_limit is not None:
            current_count = member_repo.count_for_org(self.db, invite.organization_id)
            if current_count >= seats_limit:
                raise PaymentRequiredError(
                    message="Seat limit reached — upgrade your plan to add more members",
                    details={"seats_limit": seats_limit, "current": current_count},
                )

        member_repo.create(
            self.db,
            organization_id=invite.organization_id,
            user_id=accepting_user_id,
            role=invite.role,
        )
        invitation_repo.accept(self.db, invite, accepted_by_user_id=accepting_user_id)
        logger.info(
            "Invitation %s accepted by user %s (org %s)",
            invite.id, accepting_user_id, invite.organization_id,
        )
        return invite

    def revoke(self, token: str, requester_id: str):
        """Revoke a pending invitation."""
        invite = invitation_repo.get_by_token(self.db, token)
        if not invite:
            raise NotFoundError(message="Invitation not found")

        if invite.status != InvitationStatus.PENDING.value:
            raise BadRequestError(
                message="Only pending invitations can be revoked",
                details={"status": invite.status},
            )

        requester = member_repo.get(
            self.db, organization_id=invite.organization_id, user_id=requester_id
        )
        accepting_user = user_repo.get_by_id(self.db, requester_id)
        is_own_invite = accepting_user and accepting_user.email.lower() == invite.email

        if not is_own_invite and (
            not requester or requester.role not in (OrgRole.OWNER.value, OrgRole.ADMIN.value)
        ):
            raise AuthorizationError(message="Only Owner or Admin can revoke invitations")

        invitation_repo.revoke(self.db, invite)
        return invite


{%- elif cookiecutter.use_mongodb %}
"""Invitation service (MongoDB async).

Business logic for creating, listing, accepting, and revoking org invitations.
"""

import logging
from datetime import UTC, datetime

from app.core.config import settings
from app.core.exceptions import (
    AlreadyExistsError,
    AuthenticationError,
    AuthorizationError,
    BadRequestError,
    NotFoundError,
    PaymentRequiredError,
)
from app.db.models.organization import InvitationStatus, OrgRole
from app.repositories import invitation_repo, member_repo, organization_repo, user_repo
{%- if cookiecutter.enable_email %}
from app.services.email.service import get_email_service
{%- endif %}

logger = logging.getLogger(__name__)

_ADMIN_INVITABLE_ROLES = {OrgRole.MEMBER.value, OrgRole.VIEWER.value}


class InvitationService:
    """Service for organization invitation management."""

    async def invite(self, organization_id: str, email: str, role: str, requester_id: str):
        """Send an invitation to join an org."""
        requester = await member_repo.get(organization_id=organization_id, user_id=requester_id)
        if not requester or requester.role not in (OrgRole.OWNER.value, OrgRole.ADMIN.value):
            raise AuthorizationError(message="Only Owner or Admin can invite members")

        if requester.role == OrgRole.ADMIN.value and role not in _ADMIN_INVITABLE_ROLES:
            raise AuthorizationError(message="Admin can only invite as Member or Viewer")

        normalized_email = email.lower()

        existing_user = await user_repo.get_by_email(normalized_email)
        if existing_user:
            existing_membership = await member_repo.get(
                organization_id=organization_id, user_id=str(existing_user.id)
            )
            if existing_membership:
                raise AlreadyExistsError(
                    message="User is already a member of this organization",
                    details={"email": normalized_email},
                )

        pending = await invitation_repo.get_pending_for_org_email(
            organization_id=organization_id, email=normalized_email
        )
        if pending:
            raise AlreadyExistsError(
                message="A pending invitation already exists for this email",
                details={"email": normalized_email},
            )

        invite = await invitation_repo.create(
            organization_id=organization_id,
            email=normalized_email,
            role=role,
            invited_by_user_id=requester_id,
        )
        logger.info(
            "Invitation created for %s to org %s (role=%s) by user %s",
            normalized_email, organization_id, role, requester_id,
        )
{%- if cookiecutter.enable_email %}
        try:
            org = await organization_repo.get_by_id(organization_id)
            requester_user = await user_repo.get_by_id(requester_id)
            frontend = settings.FRONTEND_URL.rstrip("/")
            accept_url = f"{frontend}/invitations/{invite.token}"
            await get_email_service().send_invitation(
                to=normalized_email,
                inviter_name=(requester_user.full_name or requester_user.email)
                if requester_user
                else "A team member",
                org_name=org.name if org else "the organization",
                accept_url=accept_url,
            )
        except Exception:
            logger.exception("email_invitation_failed")
{%- endif %}
        return invite

    async def list_for_org(
        self,
        organization_id: str,
        requester_id: str,
        *,
        status: str | None = None,
        skip: int = 0,
        limit: int = 100,
    ):
        """List invitations. Only OWNER or ADMIN may list."""
        requester = await member_repo.get(organization_id=organization_id, user_id=requester_id)
        if not requester or requester.role not in (OrgRole.OWNER.value, OrgRole.ADMIN.value):
            raise AuthorizationError(message="Only Owner or Admin can view invitations")

        return await invitation_repo.list_for_org(organization_id, status=status, skip=skip, limit=limit)

    async def accept(self, token: str, accepting_user_id: str):
        """Accept an invitation by token."""
        invite = await invitation_repo.get_by_token(token)
        if not invite:
            raise NotFoundError(message="Invitation not found or already used")

        if invite.status != InvitationStatus.PENDING.value:
            raise BadRequestError(
                message="Invitation is no longer valid",
                details={"status": invite.status},
            )

        if invite.expires_at and invite.expires_at < datetime.now(UTC):
            await invitation_repo.revoke(invite)
            raise BadRequestError(message="Invitation has expired")

        accepting_user = await user_repo.get_by_id(accepting_user_id)
        if not accepting_user or accepting_user.email.lower() != invite.email:
            raise AuthenticationError(
                message="This invitation was sent to a different email address."
            )

        existing = await member_repo.get(
            organization_id=invite.organization_id, user_id=accepting_user_id
        )
        if existing:
            raise AlreadyExistsError(
                message="You are already a member of this organization",
                details={"org_id": invite.organization_id},
            )

        org = await organization_repo.get_by_id(invite.organization_id)
        seats_limit = getattr(org, "seats_limit", None) if org is not None else None
        if seats_limit is not None:
            current_count = await member_repo.count_for_org(invite.organization_id)
            if current_count >= seats_limit:
                raise PaymentRequiredError(
                    message="Seat limit reached — upgrade your plan to add more members",
                    details={"seats_limit": seats_limit, "current": current_count},
                )

        await member_repo.create(
            organization_id=invite.organization_id,
            user_id=accepting_user_id,
            role=invite.role,
        )
        await invitation_repo.accept(invite, accepted_by_user_id=accepting_user_id)
        logger.info(
            "Invitation %s accepted by user %s (org %s)",
            invite.id, accepting_user_id, invite.organization_id,
        )
        return invite

    async def revoke(self, token: str, requester_id: str):
        """Revoke a pending invitation."""
        invite = await invitation_repo.get_by_token(token)
        if not invite:
            raise NotFoundError(message="Invitation not found")

        if invite.status != InvitationStatus.PENDING.value:
            raise BadRequestError(
                message="Only pending invitations can be revoked",
                details={"status": invite.status},
            )

        requester = await member_repo.get(
            organization_id=invite.organization_id, user_id=requester_id
        )
        accepting_user = await user_repo.get_by_id(requester_id)
        is_own_invite = accepting_user and accepting_user.email.lower() == invite.email

        if not is_own_invite and (
            not requester or requester.role not in (OrgRole.OWNER.value, OrgRole.ADMIN.value)
        ):
            raise AuthorizationError(message="Only Owner or Admin can revoke invitations")

        await invitation_repo.revoke(invite)
        return invite


{%- else %}
"""Invitation service — not configured."""
{%- endif %}
