{%- if cookiecutter.enable_teams %}
{%- if cookiecutter.use_postgresql %}
"""Organization service (PostgreSQL async).

Business logic for organization management: create, list, update, delete,
and Personal Org auto-creation on user registration.
"""

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AlreadyExistsError, AuthorizationError, BadRequestError, NotFoundError
from app.db.models.organization import OrgRole, Organization, OrganizationMember
from app.repositories import invitation_repo, member_repo, organization_repo
from app.schemas.organization import OrganizationCreate, OrganizationRead, OrganizationUpdate
{%- if cookiecutter.enable_billing and cookiecutter.enable_credits_system %}
from app.services.billing.credit_service import CreditService
{%- endif %}

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

    async def get_for_user(self, org_id: UUID, user_id: UUID) -> tuple[Organization, OrganizationMember]:
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
            result.append({
                "org": org,
                "role": membership.role if membership else OrgRole.MEMBER.value,
                "member_count": count,
            })
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
{%- if cookiecutter.enable_billing and cookiecutter.enable_credits_system %}
        if settings.CREDITS_FREE_TIER_GRANT > 0:
            try:
                await CreditService(self.db).grant_signup_bonus(organization_id=org.id)
            except Exception:
                logger.exception(
                    "free_tier_grant_failed", extra={"org_id": str(org.id)}
                )
{%- endif %}
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


{%- elif cookiecutter.use_sqlite %}
"""Organization service (SQLite sync).

Business logic for organization management: create, list, update, delete,
and Personal Org auto-creation on user registration.
"""

from sqlalchemy.orm import Session

from app.core.exceptions import AlreadyExistsError, AuthorizationError, BadRequestError, NotFoundError
from app.db.models.organization import OrgRole, Organization, OrganizationMember
from app.repositories import invitation_repo, member_repo, organization_repo
from app.schemas.organization import OrganizationCreate, OrganizationUpdate


class OrganizationService:
    """Service for organization business logic."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, org_id: str) -> Organization:
        org = organization_repo.get_by_id(self.db, org_id)
        if not org:
            raise NotFoundError(message="Organization not found", details={"org_id": org_id})
        return org

    def get_for_user(self, org_id: str, user_id: str) -> tuple[Organization, OrganizationMember]:
        """Get org and verify current user is a member. Returns (org, membership)."""
        membership = member_repo.get(self.db, organization_id=org_id, user_id=user_id)
        if not membership:
            raise NotFoundError(message="Organization not found", details={"org_id": org_id})
        org = organization_repo.get_by_id(self.db, org_id)
        if not org:
            raise NotFoundError(message="Organization not found", details={"org_id": org_id})
        return org, membership

    def list_for_user(self, user_id: str) -> list[dict]:
        """List all orgs the user is a member of, enriched with role and member_count."""
        orgs = organization_repo.list_for_user(self.db, user_id)
        result = []
        for org in orgs:
            membership = member_repo.get(self.db, organization_id=org.id, user_id=user_id)
            count = organization_repo.count_members(self.db, org.id)
            result.append({
                "org": org,
                "role": membership.role if membership else OrgRole.MEMBER.value,
                "member_count": count,
            })
        return result

    def create(self, data: OrganizationCreate, owner_id: str) -> Organization:
        """Create a new team organization (non-personal)."""
        slug = data.slug
        if slug:
            if organization_repo.slug_exists(self.db, slug):
                raise AlreadyExistsError(message="Slug already taken", details={"slug": slug})
        else:
            slug = organization_repo.generate_unique_slug(self.db, data.name)

        org = organization_repo.create(
            self.db,
            name=data.name,
            slug=slug,
            created_by_user_id=owner_id,
            is_personal=False,
        )
        member_repo.create(
            self.db,
            organization_id=org.id,
            user_id=owner_id,
            role=OrgRole.OWNER.value,
        )
        return org

    def create_personal_org(self, user_id: str, email: str) -> Organization:
        """Create the Personal Organization for a newly registered user."""
        slug = organization_repo.generate_unique_slug(self.db, email.split("@")[0])
        org = organization_repo.create(
            self.db,
            name="Personal",
            slug=slug,
            created_by_user_id=user_id,
            is_personal=True,
        )
        member_repo.create(
            self.db,
            organization_id=org.id,
            user_id=user_id,
            role=OrgRole.OWNER.value,
        )
        return org

    def update(self, org_id: str, data: OrganizationUpdate, requester_id: str) -> Organization:
        """Update org metadata. Requires ADMIN or OWNER role."""
        org, membership = self.get_for_user(org_id, requester_id)
        if membership.role not in (OrgRole.OWNER.value, OrgRole.ADMIN.value):
            raise AuthorizationError(message="Only Owner or Admin can update the organization")
        return organization_repo.update(self.db, org, name=data.name, avatar_url=data.avatar_url)

    def delete(self, org_id: str, requester_id: str) -> None:
        """Delete org. Requires OWNER role. Personal orgs cannot be deleted."""
        org, membership = self.get_for_user(org_id, requester_id)
        if org.is_personal:
            raise BadRequestError(message="Personal organization cannot be deleted")
        if membership.role != OrgRole.OWNER.value:
            raise AuthorizationError(message="Only the Owner can delete the organization")
        organization_repo.delete(self.db, org)


{%- elif cookiecutter.use_mongodb %}
"""Organization service (MongoDB).

Business logic for organization management.
"""

from app.core.exceptions import AlreadyExistsError, AuthorizationError, BadRequestError, NotFoundError
from app.db.models.organization import OrgRole, Organization
from app.repositories import member_repo, organization_repo
from app.schemas.organization import OrganizationCreate, OrganizationUpdate


class OrganizationService:
    """Service for organization business logic."""

    async def get_by_id(self, org_id: str) -> Organization:
        org = await organization_repo.get_by_id(org_id)
        if not org:
            raise NotFoundError(message="Organization not found", details={"org_id": org_id})
        return org

    async def get_for_user(self, org_id: str, user_id: str):
        membership = await member_repo.get(organization_id=org_id, user_id=user_id)
        if not membership:
            raise NotFoundError(message="Organization not found", details={"org_id": org_id})
        org = await organization_repo.get_by_id(org_id)
        if not org:
            raise NotFoundError(message="Organization not found", details={"org_id": org_id})
        return org, membership

    async def list_for_user(self, user_id: str) -> list[dict]:
        orgs = await organization_repo.list_for_user(user_id)
        result = []
        for org in orgs:
            membership = await member_repo.get(organization_id=str(org.id), user_id=user_id)
            count = await member_repo.count_for_org(str(org.id))
            result.append({
                "org": org,
                "role": membership.role if membership else OrgRole.MEMBER.value,
                "member_count": count,
            })
        return result

    async def create(self, data: OrganizationCreate, owner_id: str) -> Organization:
        slug = data.slug
        if slug:
            if await organization_repo.slug_exists(slug):
                raise AlreadyExistsError(message="Slug already taken", details={"slug": slug})
        else:
            slug = await organization_repo.generate_unique_slug(data.name)

        org = await organization_repo.create(
            name=data.name,
            slug=slug,
            created_by_user_id=owner_id,
            is_personal=False,
        )
        await member_repo.create(
            organization_id=str(org.id),
            user_id=owner_id,
            role=OrgRole.OWNER.value,
        )
        return org

    async def create_personal_org(self, user_id: str, email: str) -> Organization:
        slug = await organization_repo.generate_unique_slug(email.split("@")[0])
        org = await organization_repo.create(
            name="Personal",
            slug=slug,
            created_by_user_id=user_id,
            is_personal=True,
        )
        await member_repo.create(
            organization_id=str(org.id),
            user_id=user_id,
            role=OrgRole.OWNER.value,
        )
        return org

    async def update(self, org_id: str, data: OrganizationUpdate, requester_id: str) -> Organization:
        org, membership = await self.get_for_user(org_id, requester_id)
        if membership.role not in (OrgRole.OWNER.value, OrgRole.ADMIN.value):
            raise AuthorizationError(message="Only Owner or Admin can update the organization")
        org.name = data.name or org.name
        org.avatar_url = data.avatar_url if data.avatar_url is not None else org.avatar_url
        await org.save()
        return org

    async def delete(self, org_id: str, requester_id: str) -> None:
        org, membership = await self.get_for_user(org_id, requester_id)
        if org.is_personal:
            raise BadRequestError(message="Personal organization cannot be deleted")
        if membership.role != OrgRole.OWNER.value:
            raise AuthorizationError(message="Only the Owner can delete the organization")
        await organization_repo.delete(org)


{%- else %}
"""Organization service — not configured."""
{%- endif %}
{%- else %}
"""Organization service — not configured (enable_teams=false)."""
{%- endif %}
