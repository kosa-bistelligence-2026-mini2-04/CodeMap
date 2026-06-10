"""Lifecycle email tasks — trial reminders and low-credits alerts."""

import asyncio
import logging
from typing import Any

from celery import shared_task

from app.db.session import get_worker_db_context
from app.services.billing import BillingService

logger = logging.getLogger(__name__)


async def _send_trial_reminders() -> int:
    async with get_worker_db_context() as db:
        return await BillingService(db).send_trial_ending_reminders()


async def _send_low_credits_alerts() -> int:
    async with get_worker_db_context() as db:
        return await BillingService(db).send_low_credits_alerts()


@shared_task(bind=True, max_retries=1, ignore_result=True)
def send_trial_reminders_task(self: Any) -> None:
    """Cron: send trial-ending reminder emails for trials expiring within 3 days."""
    try:
        count = asyncio.run(_send_trial_reminders())
        logger.info("trial_reminders_sent", extra={"count": count})
    except Exception as exc:
        logger.exception("send_trial_reminders_task_failed")
        raise self.retry(exc=exc, countdown=300) from exc


@shared_task(bind=True, max_retries=1, ignore_result=True)
def send_low_credits_alerts_task(self: Any) -> None:
    """Cron: send low-credits alert emails to orgs below threshold."""
    try:
        count = asyncio.run(_send_low_credits_alerts())
        logger.info("low_credits_alerts_sent", extra={"count": count})
    except Exception as exc:
        logger.exception("send_low_credits_alerts_task_failed")
        raise self.retry(exc=exc, countdown=300) from exc
