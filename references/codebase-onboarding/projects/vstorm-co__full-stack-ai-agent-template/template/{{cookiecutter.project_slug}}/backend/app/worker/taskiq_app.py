{%- if cookiecutter.use_taskiq %}
"""Taskiq application configuration."""

from taskiq import TaskiqScheduler
from taskiq_redis import ListQueueBroker, RedisAsyncResultBackend

from app.core.config import settings

# Create Taskiq broker with Redis
broker = ListQueueBroker(
    url=settings.TASKIQ_BROKER_URL,
).with_result_backend(
    RedisAsyncResultBackend(
        redis_url=settings.TASKIQ_RESULT_BACKEND,
    )
)

# Create scheduler for periodic tasks
scheduler = TaskiqScheduler(
    broker=broker,
    sources=["app.worker.tasks.schedules"],
)


# Startup/shutdown hooks
@broker.on_event("startup")
async def startup() -> None:
    """Initialize broker on startup."""
    pass


@broker.on_event("shutdown")
async def shutdown() -> None:
    """Cleanup on shutdown."""
    pass
{%- else %}
# Taskiq not enabled for this project
{%- endif %}
