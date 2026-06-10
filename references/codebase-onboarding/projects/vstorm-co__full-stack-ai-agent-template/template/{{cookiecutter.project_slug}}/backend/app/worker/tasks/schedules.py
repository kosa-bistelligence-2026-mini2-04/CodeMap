{%- if cookiecutter.use_taskiq %}
"""Taskiq scheduled tasks (cron-like)."""

from app.worker.taskiq_app import broker
{%- if cookiecutter.enable_email and cookiecutter.enable_billing %}
from app.worker.tasks.email_tasks import send_trial_reminders_task
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_credits_system %}
from app.worker.tasks.email_tasks import send_low_credits_alerts_task
{%- endif %}
{%- if cookiecutter.enable_credits_system %}
from app.worker.tasks.cleanup_tasks import cleanup_usage_events_task
{%- endif %}
{%- if cookiecutter.enable_rag %}
from app.worker.tasks.rag_tasks import check_scheduled_syncs
{%- endif %}

{%- if cookiecutter.enable_rag %}


@broker.task(schedule=[{"cron": "* * * * *"}])
async def scheduled_rag_sync_check() -> dict:
    """Scheduled task: check for connector sources due for sync and dispatch."""
    result = await check_scheduled_syncs.kiq()
    return {"scheduled": True, "task_id": str(result.task_id)}
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_billing %}


@broker.task(schedule=[{"cron": "0 9 * * *"}])
async def scheduled_trial_reminders() -> dict:
    """Scheduled task: send trial-ending reminder emails."""
    result = await send_trial_reminders_task.kiq()
    return {"scheduled": True, "task_id": str(result.task_id)}
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_credits_system %}


@broker.task(schedule=[{"cron": "0 */4 * * *"}])
async def scheduled_low_credits_alerts() -> dict:
    """Scheduled task: send low-credits alert emails."""
    result = await send_low_credits_alerts_task.kiq()
    return {"scheduled": True, "task_id": str(result.task_id)}
{%- endif %}
{%- if cookiecutter.enable_credits_system %}


@broker.task(schedule=[{"cron": "0 3 * * 0"}])
async def scheduled_cleanup_usage_events() -> dict:
    """Scheduled task: purge old usage events and refresh daily matview."""
    result = await cleanup_usage_events_task.kiq()
    return {"scheduled": True, "task_id": str(result.task_id)}
{%- endif %}
{%- endif %}
