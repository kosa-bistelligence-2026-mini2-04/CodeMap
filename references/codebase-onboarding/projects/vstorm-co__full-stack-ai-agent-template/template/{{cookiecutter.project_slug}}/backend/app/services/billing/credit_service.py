{%- if cookiecutter.enable_billing and cookiecutter.enable_credits_system %}
"""CreditService — atomic credit ledger operations."""

{%- if cookiecutter.use_postgresql %}
import uuid
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.billing.exceptions import InsufficientCreditsError
from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.db.models.organization import Organization
from app.db.models.credit_transaction import CreditTransaction, CreditTransactionType
import app.repositories.credit_transaction as credit_tx_repo

logger = logging.getLogger(__name__)


class CreditService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Grants
    # ------------------------------------------------------------------

    async def grant_subscription_credits(
        self,
        *,
        organization_id: uuid.UUID,
        amount: int,
        description: str,
        stripe_reference: str | None = None,
    ) -> CreditTransaction:
        org = await self._lock_org(organization_id)
        org.credits_balance += amount
        return await credit_tx_repo.create(
            self.db,
            organization_id=organization_id,
            delta=amount,
            balance_after=org.credits_balance,
            type=CreditTransactionType.GRANT_SUBSCRIPTION,
            description=description,
            stripe_reference=stripe_reference,
        )

    async def add_topup_credits(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID | None = None,
        amount: int,
        stripe_payment_intent_id: str,
    ) -> CreditTransaction:
        org = await self._lock_org(organization_id)
        org.credits_balance += amount
        return await credit_tx_repo.create(
            self.db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            delta=amount,
            balance_after=org.credits_balance,
            type=CreditTransactionType.PURCHASE_TOPUP,
            description=f"Credit top-up ({amount} credits)",
            stripe_reference=stripe_payment_intent_id,
        )

    async def grant_signup_bonus(self, *, organization_id: uuid.UUID) -> CreditTransaction:
        amount = settings.CREDITS_FREE_TIER_GRANT
        org = await self._lock_org(organization_id)
        org.credits_balance += amount
        return await credit_tx_repo.create(
            self.db,
            organization_id=organization_id,
            delta=amount,
            balance_after=org.credits_balance,
            type=CreditTransactionType.GRANT_TRIAL,
            description=f"Sign-up bonus ({amount} credits)",
        )

    # ------------------------------------------------------------------
    # Debit (hot path — keep fast, minimize lock duration)
    # ------------------------------------------------------------------

    async def debit(
        self,
        *,
        organization_id: uuid.UUID,
        actor_user_id: uuid.UUID | None = None,
        amount: int,
        type: CreditTransactionType,
        description: str,
        usage_event_id: uuid.UUID | None = None,
    ) -> CreditTransaction:
        if amount <= 0:
            raise ValueError("Amount must be positive")

        stmt = select(Organization).where(Organization.id == organization_id).with_for_update()
        result = await self.db.execute(stmt)
        org = result.scalar_one_or_none()
        if not org:
            raise NotFoundError(message="Organization not found", details={"org_id": str(organization_id)})

        if org.credits_balance < amount:
            raise InsufficientCreditsError(
                message=f"Need {amount} credits, have {org.credits_balance}",
                details={"required": amount, "available": org.credits_balance},
            )

        org.credits_balance -= amount
        new_balance = org.credits_balance

        tx = await credit_tx_repo.create(
            self.db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            delta=-amount,
            balance_after=new_balance,
            type=type,
            description=description,
            usage_event_id=usage_event_id,
        )

        if new_balance < settings.CREDITS_LOW_THRESHOLD and (new_balance + amount) >= settings.CREDITS_LOW_THRESHOLD:
            logger.warning(
                "credits_low_threshold_crossed",
                extra={"org_id": str(organization_id), "balance": new_balance},
            )

        return tx

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    async def get_balance(self, organization_id: uuid.UUID) -> int:
        org = await self.db.get(Organization, organization_id)
        if not org:
            raise NotFoundError(message="Organization not found", details={"org_id": str(organization_id)})
        return org.credits_balance

    async def get_history(
        self,
        organization_id: uuid.UUID,
        *,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[CreditTransaction], int]:
        return await credit_tx_repo.list_for_org(self.db, organization_id, skip=skip, limit=limit)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _lock_org(self, organization_id: uuid.UUID) -> Organization:
        stmt = select(Organization).where(Organization.id == organization_id).with_for_update()
        result = await self.db.execute(stmt)
        org = result.scalar_one_or_none()
        if not org:
            raise NotFoundError(message="Organization not found", details={"org_id": str(organization_id)})
        return org

{%- elif cookiecutter.use_sqlite %}
import logging
from sqlalchemy.orm import Session

from app.services.billing.exceptions import InsufficientCreditsError
from app.core.exceptions import NotFoundError
from app.db.models.organization import Organization
from app.db.models.credit_transaction import CreditTransaction, CreditTransactionType
import app.repositories.credit_transaction as credit_tx_repo

logger = logging.getLogger(__name__)


class CreditService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def grant_credits(self, *, organization_id: str, amount: int, type: CreditTransactionType, description: str, stripe_reference: str | None = None) -> CreditTransaction:
        from sqlalchemy import select
        org = self.db.get(Organization, organization_id)
        if not org:
            raise NotFoundError(message="Organization not found", details={"org_id": organization_id})
        org.credits_balance = (org.credits_balance or 0) + amount
        return credit_tx_repo.create(
            self.db,
            organization_id=organization_id,
            delta=amount,
            balance_after=org.credits_balance,
            type=type,
            description=description,
            stripe_reference=stripe_reference,
        )

    def debit(
        self,
        *,
        organization_id: str,
        actor_user_id: str | None = None,
        amount: int,
        type: CreditTransactionType,
        description: str,
        usage_event_id: str | None = None,
    ) -> CreditTransaction:
        if amount <= 0:
            raise ValueError("Amount must be positive")

        org = self.db.get(Organization, organization_id)
        if not org:
            raise NotFoundError(message="Organization not found", details={"org_id": organization_id})

        balance = org.credits_balance or 0
        if balance < amount:
            raise InsufficientCreditsError(
                message=f"Need {amount} credits, have {balance}",
                details={"required": amount, "available": balance},
            )

        org.credits_balance = balance - amount
        return credit_tx_repo.create(
            self.db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            delta=-amount,
            balance_after=org.credits_balance,
            type=type,
            description=description,
            usage_event_id=usage_event_id,
        )

    def get_balance(self, organization_id: str) -> int:
        org = self.db.get(Organization, organization_id)
        if not org:
            raise NotFoundError(message="Organization not found", details={"org_id": organization_id})
        return org.credits_balance or 0

    def get_history(self, organization_id: str, *, skip: int = 0, limit: int = 50) -> tuple[list[CreditTransaction], int]:
        return credit_tx_repo.list_for_org(self.db, organization_id, skip=skip, limit=limit)

{%- elif cookiecutter.use_mongodb %}
import logging
from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.services.billing.exceptions import InsufficientCreditsError
from app.core.exceptions import NotFoundError
from app.db.models.credit_transaction import CreditTransaction, CreditTransactionType
import app.repositories.credit_transaction as credit_tx_repo

logger = logging.getLogger(__name__)


class CreditService:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self.db = db

    async def debit(
        self,
        *,
        organization_id: str,
        actor_user_id: str | None = None,
        amount: int,
        type: CreditTransactionType,
        description: str,
        usage_event_id: str | None = None,
    ) -> CreditTransaction:
        if amount <= 0:
            raise ValueError("Amount must be positive")

        from bson import ObjectId
        result = await self.db.organizations.find_one_and_update(
            filter={"_id": ObjectId(organization_id), "credits_balance": {"$gte": amount}},
            update={"$inc": {"credits_balance": -amount}},
            return_document=ReturnDocument.AFTER,
        )
        if result is None:
            org = await self.db.organizations.find_one({"_id": ObjectId(organization_id)})
            if not org:
                raise NotFoundError(message="Organization not found", details={"org_id": organization_id})
            raise InsufficientCreditsError(
                message=f"Need {amount} credits, have {org.get('credits_balance', 0)}",
                details={"required": amount, "available": org.get("credits_balance", 0)},
            )

        return await credit_tx_repo.create(
            self.db,
            organization_id=organization_id,
            actor_user_id=actor_user_id,
            delta=-amount,
            balance_after=result["credits_balance"],
            type=type,
            description=description,
            usage_event_id=usage_event_id,
        )

    async def grant_credits(self, *, organization_id: str, amount: int, type: CreditTransactionType, description: str, stripe_reference: str | None = None) -> CreditTransaction:
        from bson import ObjectId
        result = await self.db.organizations.find_one_and_update(
            filter={"_id": ObjectId(organization_id)},
            update={"$inc": {"credits_balance": amount}},
            return_document=ReturnDocument.AFTER,
        )
        if not result:
            raise NotFoundError(message="Organization not found", details={"org_id": organization_id})

        return await credit_tx_repo.create(
            self.db,
            organization_id=organization_id,
            delta=amount,
            balance_after=result["credits_balance"],
            type=type,
            description=description,
            stripe_reference=stripe_reference,
        )

    async def get_balance(self, organization_id: str) -> int:
        from bson import ObjectId
        org = await self.db.organizations.find_one({"_id": ObjectId(organization_id)})
        if not org:
            raise NotFoundError(message="Organization not found", details={"org_id": organization_id})
        return org.get("credits_balance", 0)

{%- endif %}
{%- else %}
"""credit_service — not enabled (enable_billing=false or enable_credits_system=false)."""
{%- endif %}
