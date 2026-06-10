{%- if cookiecutter.use_arq %}
"""ARQ (Async Redis Queue) application configuration."""

import logging
from typing import Any

from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings
{%- if cookiecutter.enable_rag %}
from app.worker.tasks.rag_tasks import check_scheduled_syncs, sync_single_source_task
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_billing %}
from app.worker.tasks.email_tasks import send_trial_reminders_task
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_credits_system %}
from app.worker.tasks.email_tasks import send_low_credits_alerts_task
{%- endif %}
{%- if cookiecutter.enable_credits_system %}
from app.worker.tasks.cleanup_tasks import cleanup_usage_events_task
{%- endif %}

logger = logging.getLogger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    """Initialize resources on worker startup."""
    logger.info("ARQ worker starting up...")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Cleanup resources on worker shutdown."""
    logger.info("ARQ worker shutting down...")


class WorkerSettings:
    """ARQ Worker configuration. Used by the ARQ CLI: arq app.worker.arq_app.WorkerSettings."""

    redis_settings = RedisSettings(
        host=settings.ARQ_REDIS_HOST,
        port=settings.ARQ_REDIS_PORT,
        password=settings.ARQ_REDIS_PASSWORD or None,
        database=settings.ARQ_REDIS_DB,
    )

    functions = [
{%- if cookiecutter.enable_rag %}
        sync_single_source_task,
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_billing %}
        send_trial_reminders_task,
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_credits_system %}
        send_low_credits_alerts_task,
{%- endif %}
{%- if cookiecutter.enable_credits_system %}
        cleanup_usage_events_task,
{%- endif %}
    ]

    cron_jobs = [
{%- if cookiecutter.enable_rag %}
        cron(check_scheduled_syncs),
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_billing %}
        cron(send_trial_reminders_task, hour=9, minute=0),
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_credits_system %}
        cron(send_low_credits_alerts_task, minute=0),
{%- endif %}
{%- if cookiecutter.enable_credits_system %}
        cron(cleanup_usage_events_task, weekday=0, hour=3, minute=0),
{%- endif %}
    ]

    on_startup = startup
    on_shutdown = shutdown

    max_jobs = 10
    job_timeout = 300
    keep_result = 3600
    poll_delay = 0.5
    queue_read_limit = 100
{%- endif %}
