{%- if cookiecutter.use_slack or cookiecutter.use_telegram %}
"""In-process handler for channel-bot webhook events (Telegram, Slack).

Dispatched via FastAPI ``BackgroundTasks`` from the webhook routes so the platform
gets a fast 200 OK while routing/AI happens in the background.
"""

import logging
from typing import Any

from app.services.channels.router import ChannelMessageRouter
{%- if cookiecutter.use_postgresql %}
from app.db.session import get_db_context
{%- elif cookiecutter.use_sqlite %}
from contextlib import contextmanager

from app.db.session import get_db_session
{%- endif %}

logger = logging.getLogger(__name__)


async def process_channel_event(incoming: Any) -> None:
    """Route an incoming channel event to its handler.

    Errors are logged with full traceback but never re-raised — the response to the
    platform has already been sent, and an unhandled exception here would just become
    a noisy stack trace in the API process logs.
    """
    try:
{%- if cookiecutter.use_postgresql %}
        async with get_db_context() as db:
            await ChannelMessageRouter().route(incoming, db)
{%- elif cookiecutter.use_sqlite %}
        with contextmanager(get_db_session)() as db:
            await ChannelMessageRouter().route(incoming, db)
{%- elif cookiecutter.use_mongodb %}
        await ChannelMessageRouter().route(incoming, None)
{%- endif %}
    except Exception:
        logger.exception("channel_event_processing_failed")
{%- else %}
"""Channel background tasks — no channels configured."""
{%- endif %}
