{%- if cookiecutter.enable_billing %}
"""Handlers for customer.* webhook events."""

import logging
{%- if cookiecutter.use_postgresql %}
import stripe
from sqlalchemy.ext.asyncio import AsyncSession

import app.repositories.organization as org_repo

logger = logging.getLogger(__name__)


async def handle_customer_created(db: AsyncSession, event: stripe.Event) -> None:
    customer = event.data.object
    org_id = customer.metadata.get("org_id")
    if org_id:
        logger.info(
            "stripe_customer_created",
            extra={"customer_id": customer.id, "org_id": org_id},
        )


async def handle_customer_updated(db: AsyncSession, event: stripe.Event) -> None:
    customer = event.data.object
    logger.debug("stripe_customer_updated", extra={"customer_id": customer.id})


async def handle_customer_deleted(db: AsyncSession, event: stripe.Event) -> None:
    customer = event.data.object
    logger.warning("stripe_customer_deleted", extra={"customer_id": customer.id})
    org = await org_repo.get_by_stripe_customer(db, customer.id)
    if org:
        org.stripe_customer_id = None
        await db.flush()

{%- elif cookiecutter.use_sqlite %}
import stripe
from sqlalchemy.orm import Session

import app.repositories.organization as org_repo

logger = logging.getLogger(__name__)


def handle_customer_created(db: Session, event: stripe.Event) -> None:
    logger.info("stripe_customer_created", extra={"customer_id": event.data.object.id})


def handle_customer_updated(db: Session, event: stripe.Event) -> None:
    logger.debug("stripe_customer_updated", extra={"customer_id": event.data.object.id})


def handle_customer_deleted(db: Session, event: stripe.Event) -> None:
    customer = event.data.object
    logger.warning("stripe_customer_deleted", extra={"customer_id": customer.id})
    org = org_repo.get_by_stripe_customer(db, customer.id)
    if org:
        org.stripe_customer_id = None
        db.flush()

{%- elif cookiecutter.use_mongodb %}
import stripe
from motor.motor_asyncio import AsyncIOMotorDatabase

import app.repositories.organization as org_repo

logger = logging.getLogger(__name__)


async def handle_customer_created(db: AsyncIOMotorDatabase, event: stripe.Event) -> None:
    logger.info("stripe_customer_created", extra={"customer_id": event.data.object.id})


async def handle_customer_updated(db: AsyncIOMotorDatabase, event: stripe.Event) -> None:
    logger.debug("stripe_customer_updated", extra={"customer_id": event.data.object.id})


async def handle_customer_deleted(db: AsyncIOMotorDatabase, event: stripe.Event) -> None:
    customer = event.data.object
    logger.warning("stripe_customer_deleted", extra={"customer_id": customer.id})
    org = await org_repo.get_by_stripe_customer(db, customer.id)
    if org:
        org.stripe_customer_id = None
        await org.save()

{%- endif %}
{%- else %}
"""customer_events — not enabled (enable_billing=false)."""
{%- endif %}
