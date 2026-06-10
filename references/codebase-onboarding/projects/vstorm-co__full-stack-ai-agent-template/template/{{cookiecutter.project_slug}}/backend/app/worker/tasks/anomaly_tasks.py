"""Periodic usage anomaly detection.

Iterates organizations with recent usage and emits a Slack alert when current-hour
credit consumption exceeds the rolling-24h hourly baseline by ``_SPIKE_MULTIPLIER``.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from celery import shared_task
from sqlalchemy import distinct, select

from app.db.models.credit_transaction import UsageEvent
from app.db.session import get_worker_db_context
from app.services.anomaly_detection import detect_spike, send_slack_alert

logger = logging.getLogger(__name__)


async def _run_anomaly_check() -> int:
    """Scan orgs with usage in the last 24h; alert on spikes. Returns alert count."""
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    alerted = 0
    async with get_worker_db_context() as db:
        rows = await db.execute(
            select(distinct(UsageEvent.organization_id)).where(
                UsageEvent.created_at >= cutoff
            )
        )
        org_ids = [row[0] for row in rows.all()]
        for org_id in org_ids:
            try:
                spike = await detect_spike(db, org_id)
                if spike:
                    await send_slack_alert(spike)
                    alerted += 1
            except Exception:
                logger.exception(
                    "anomaly_check_failed", extra={"organization_id": str(org_id)}
                )
    return alerted


@shared_task(bind=True, max_retries=1, ignore_result=True)
def detect_usage_spikes_task(self: Any) -> None:
    """Cron: scan orgs for hourly credit spikes and post a Slack alert if found."""
    try:
        alerts = asyncio.run(_run_anomaly_check())
        logger.info("anomaly_check_done", extra={"alerts": alerts})
    except Exception as exc:
        logger.exception("anomaly_check_task_failed")
        raise self.retry(exc=exc, countdown=600) from exc
