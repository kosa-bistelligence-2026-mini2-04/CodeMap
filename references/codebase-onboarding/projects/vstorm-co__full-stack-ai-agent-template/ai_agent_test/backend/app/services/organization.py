"""Organization service (PostgreSQL async).

Business logic for organization management: create, list, update, delete,
and Personal Org auto-creation on user registration.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AlreadyExistsError,
    AuthorizationError,
    BadRequestError,
    NotFoundError,
)
from app.db.models.organization import Organization, OrganizationMember, OrgRole
from app.repositories import member_repo, organization_repo
from app.schemas.organization import OrganizationCreate, OrganizationUpdate
from app.services.billing.credit_service import CreditService

logger = logging.getLogger(__name__)


class OrganizationService:
    """Service for organization business logic."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, org_id: UUID) -> Organization:
        org = await organization_repo.get_by_id(self.db, org_id)
        if not org:
            raise NotFoundError(message="Organization not found", details={"org_id": str(org_id)})
        return org

    async def get_for_user(
        self, org_id: UUID, user_id: UUID
    ) -> tuple[Organization, OrganizationMember]:
        """Get org and verify current user is a member. Returns (org, membership)."""
        membership = await member_repo.get(self.db, organization_id=org_id, user_id=user_id)
        if not membership:
            raise NotFoundError(message="Organization not found", details={"org_id": str(org_id)})
        org = await organization_repo.get_by_id(self.db, org_id)
        if not org:
            raise NotFoundError(message="Organization not found", details={"org_id": str(org_id)})
        return org, membership

    async def list_for_user(self, user_id: UUID) -> list[dict]:
        """List all orgs the user is a member of, enriched with role and member_count."""
        orgs = await organization_repo.list_for_user(self.db, user_id)
        result = []
        for org in orgs:
            membership = await member_repo.get(self.db, organization_id=org.id, user_id=user_id)
            count = await organization_repo.count_members(self.db, org.id)
            result.append(
                {
                    "org": org,
                    "role": membership.role if membership else OrgRole.MEMBER.value,
                    "member_count": count,
                }
            )
        return result

    async def create(self, data: OrganizationCreate, owner_id: UUID) -> Organization:
        """Create a new team organization (non-personal)."""
        slug = data.slug
        if slug:
            if await organization_repo.slug_exists(self.db, slug):
                raise AlreadyExistsError(
                    message="Slug already taken",
                    details={"slug": slug},
                )
        else:
            slug = await organization_repo.generate_unique_slug(self.db, data.name)

        org = await organization_repo.create(
            self.db,
            name=data.name,
            slug=slug,
            created_by_user_id=owner_id,
            is_personal=False,
        )
        await member_repo.create(
            self.db,
            organization_id=org.id,
            user_id=owner_id,
            role=OrgRole.OWNER.value,
        )
        return org

    async def create_personal_org(self, user_id: UUID, email: str) -> Organization:
        """Create the Personal Organization for a newly registered user.

        Also grants the configured free-tier credit bonus so AI usage works on
        the free plan up to the granted amount.
        """
        slug = await organization_repo.generate_unique_slug(self.db, email.split("@")[0])
        org = await organization_repo.create(
            self.db,
            name="Personal",
            slug=slug,
            created_by_user_id=user_id,
            is_personal=True,
        )
        await member_repo.create(
            self.db,
            organization_id=org.id,
            user_id=user_id,
            role=OrgRole.OWNER.value,
        )
        if settings.CREDITS_FREE_TIER_GRANT > 0:
            try:
                await CreditService(self.db).grant_signup_bonus(organization_id=org.id)
            except Exception:
                logger.exception("free_tier_grant_failed", extra={"org_id": str(org.id)})
        return org

    async def update(
        self,
        org_id: UUID,
        data: OrganizationUpdate,
        requester_id: UUID,
    ) -> Organization:
        """Update org metadata. Requires ADMIN or OWNER role."""
        org, membership = await self.get_for_user(org_id, requester_id)
        if membership.role not in (OrgRole.OWNER.value, OrgRole.ADMIN.value):
            raise AuthorizationError(message="Only Owner or Admin can update the organization")

        return await organization_repo.update(
            self.db,
            org,
            name=data.name,
            avatar_url=data.avatar_url,
        )

    async def delete(self, org_id: UUID, requester_id: UUID) -> None:
        """Delete org. Requires OWNER role. Personal orgs cannot be deleted."""
        org, membership = await self.get_for_user(org_id, requester_id)

        if org.is_personal:
            raise BadRequestError(message="Personal organization cannot be deleted")
        if membership.role != OrgRole.OWNER.value:
            raise AuthorizationError(message="Only the Owner can delete the organization")

        await organization_repo.delete(self.db, org)
