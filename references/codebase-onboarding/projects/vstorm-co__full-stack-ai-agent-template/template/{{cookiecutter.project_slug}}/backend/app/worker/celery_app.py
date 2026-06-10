{%- if cookiecutter.use_celery %}
"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings
{%- if cookiecutter.enable_logfire and cookiecutter.logfire_celery %}
from app.core.logfire_setup import instrument_celery
{%- endif %}

celery_app = Celery(
    "{{ cookiecutter.project_slug }}",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="{{ cookiecutter.timezone }}",
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
)

celery_app.autodiscover_tasks(["app.worker.tasks"])

celery_app.conf.beat_schedule = {
{%- if cookiecutter.enable_rag %}
    "rag-sync-check": {
        "task": "app.worker.tasks.rag_tasks.check_scheduled_syncs",
        "schedule": 60.0,
    },
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_billing %}
    "send-trial-reminders": {
        "task": "app.worker.tasks.email_tasks.send_trial_reminders_task",
        "schedule": crontab(hour=9, minute=0),
    },
{%- endif %}
{%- if cookiecutter.enable_email and cookiecutter.enable_credits_system %}
    "send-low-credits-alerts": {
        "task": "app.worker.tasks.email_tasks.send_low_credits_alerts_task",
        "schedule": crontab(minute=0, hour="*/4"),
    },
{%- endif %}
{%- if cookiecutter.enable_credits_system %}
    "cleanup-usage-events": {
        "task": "app.worker.tasks.cleanup_tasks.cleanup_usage_events_task",
        "schedule": crontab(hour=3, minute=0, day_of_week=0),
    },
    "detect-usage-spikes": {
        "task": "app.worker.tasks.anomaly_tasks.detect_usage_spikes_task",
        "schedule": crontab(minute=15),
    },
    "refresh-usage-matview": {
        "task": "app.worker.tasks.cleanup_tasks.refresh_usage_matview_task",
        "schedule": 300.0,  # 5 minutes
    },
{%- endif %}
}
{%- if cookiecutter.enable_logfire and cookiecutter.logfire_celery %}


instrument_celery()
{%- endif %}
{%- endif %}
