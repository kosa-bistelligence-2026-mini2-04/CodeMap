{%- if cookiecutter.enable_billing and (cookiecutter.use_postgresql or cookiecutter.use_sqlite or cookiecutter.use_mongodb) %}
"""Sync Stripe Products/Prices to local DB.

Run after any changes to your Stripe Dashboard catalog:
    uv run {{ cookiecutter.project_slug }} cmd sync-stripe-plans

Convention:
  - Each Stripe Product must have metadata.code  (plan code in our DB)
  - Optional metadata.features                   (JSON object)
  - Optional metadata.monthly_credits            (integer)
  - Optional metadata.included_seats             (integer)
  - Optional metadata.extra_seat_cents           (integer)
  - Optional metadata.credits_grant              (for one-time top-up prices)
"""
{% if cookiecutter.use_postgresql or cookiecutter.use_mongodb %}
import asyncio
{% endif %}
import json
import click
import stripe

from app.commands import command, info, success, warning, error
from app.core.config import settings

{%- if cookiecutter.use_postgresql %}
from sqlalchemy.ext.asyncio import AsyncSession
import app.repositories.plan as plan_repo


async def _run_sync() -> None:
    from app.db.session import async_session_maker

    stripe.api_key = settings.STRIPE_SECRET_KEY

    async with async_session_maker() as db:
        products = stripe.Product.list(active=True, limit=100)
        synced_plans = 0
        synced_prices = 0

        for product in products.auto_paging_iter():
            meta = product.metadata or {}
            code = meta.get("code", product.id)

            plan = await plan_repo.upsert_plan(
                db,
                code=code,
                display_name=product.name,
                description=product.description,
                is_active=product.active,
                features=json.loads(meta.get("features", "{}")),
                monthly_credits_base=int(meta.get("monthly_credits", 0)),
                monthly_credits_per_seat=int(meta.get("monthly_credits_per_seat", 0)),
                included_seats=int(meta.get("included_seats", 1)),
                extra_seat_amount_cents=int(meta.get("extra_seat_cents", 0)),
            )
            synced_plans += 1
            info(f"  Plan: {plan.code} — {plan.display_name}")

            prices = stripe.Price.list(product=product.id, active=True, limit=100)
            for stripe_price in prices.auto_paging_iter():
                await plan_repo.upsert_price(
                    db,
                    stripe_price_id=stripe_price.id,
                    plan_id=plan.id,
                    interval=stripe_price.recurring.interval if stripe_price.recurring else "one_time",
                    amount_cents=stripe_price.unit_amount or 0,
                    currency=stripe_price.currency,
                    billing_scheme=stripe_price.billing_scheme,
                    tiers_mode=stripe_price.tiers_mode,
                    credits_grant=int(stripe_price.metadata.get("credits_grant", 0)) or None,
                )
                synced_prices += 1

        await db.commit()
        success(f"Synced {synced_plans} plans and {synced_prices} prices from Stripe.")


@command("sync-stripe-plans", help="Pull active products/prices from Stripe and upsert into local DB")
def sync_stripe_plans() -> None:
    asyncio.run(_run_sync())

{%- elif cookiecutter.use_sqlite %}
from sqlalchemy.orm import Session
import app.repositories.plan as plan_repo


def _run_sync() -> None:
    from app.db.session import SessionLocal

    stripe.api_key = settings.STRIPE_SECRET_KEY

    with SessionLocal() as db:
        products = stripe.Product.list(active=True, limit=100)
        synced_plans = 0
        synced_prices = 0

        for product in products.auto_paging_iter():
            meta = product.metadata or {}
            code = meta.get("code", product.id)

            plan = plan_repo.upsert_plan(
                db,
                code=code,
                display_name=product.name,
                description=product.description,
                is_active=product.active,
                features=json.loads(meta.get("features", "{}")),
                monthly_credits_base=int(meta.get("monthly_credits", 0)),
                included_seats=int(meta.get("included_seats", 1)),
            )
            synced_plans += 1
            info(f"  Plan: {plan.code} — {plan.display_name}")

            prices = stripe.Price.list(product=product.id, active=True, limit=100)
            for stripe_price in prices.auto_paging_iter():
                plan_repo.upsert_price(
                    db,
                    stripe_price_id=stripe_price.id,
                    plan_id=str(plan.id),
                    interval=stripe_price.recurring.interval if stripe_price.recurring else "one_time",
                    amount_cents=stripe_price.unit_amount or 0,
                    currency=stripe_price.currency,
                    billing_scheme=stripe_price.billing_scheme,
                    credits_grant=int(stripe_price.metadata.get("credits_grant", 0)) or None,
                )
                synced_prices += 1

        db.commit()
        success(f"Synced {synced_plans} plans and {synced_prices} prices from Stripe.")


@command("sync-stripe-plans", help="Pull active products/prices from Stripe and upsert into local DB")
def sync_stripe_plans() -> None:
    _run_sync()

{%- elif cookiecutter.use_mongodb %}
from beanie import init_beanie
import app.repositories.plan as plan_repo


async def _run_sync() -> None:
    from app.db.session import get_mongo_db
    from app.db.models.plan import Plan, Price

    stripe.api_key = settings.STRIPE_SECRET_KEY

    db = get_mongo_db()
    await init_beanie(database=db, document_models=[Plan, Price])

    products = stripe.Product.list(active=True, limit=100)
    synced_plans = 0
    synced_prices = 0

    for product in products.auto_paging_iter():
        meta = product.metadata or {}
        code = meta.get("code", product.id)

        existing = await plan_repo.get_plan_by_code(db, code)
        if existing:
            existing.display_name = product.name
            await existing.save()
            plan = existing
        else:
            plan = Plan(
                code=code,
                display_name=product.name,
                description=product.description,
                is_active=product.active,
            )
            await plan.insert()

        synced_plans += 1
        info(f"  Plan: {plan.code} — {plan.display_name}")

        prices = stripe.Price.list(product=product.id, active=True, limit=100)
        for stripe_price in prices.auto_paging_iter():
            existing_price = await plan_repo.get_price_by_stripe_id(db, stripe_price.id)
            if existing_price:
                existing_price.amount_cents = stripe_price.unit_amount or 0
                await existing_price.save()
            else:
                from app.db.models.plan import Price as PriceModel
                p = PriceModel(
                    plan_id=str(plan.id),
                    stripe_price_id=stripe_price.id,
                    interval=stripe_price.recurring.interval if stripe_price.recurring else "one_time",
                    amount_cents=stripe_price.unit_amount or 0,
                    currency=stripe_price.currency,
                )
                await p.insert()
            synced_prices += 1

    success(f"Synced {synced_plans} plans and {synced_prices} prices from Stripe.")


@command("sync-stripe-plans", help="Pull active products/prices from Stripe and upsert into local DB")
def sync_stripe_plans() -> None:
    asyncio.run(_run_sync())

{%- endif %}
{%- else %}
"""sync_stripe_plans — not enabled (enable_billing=false)."""
{%- endif %}
