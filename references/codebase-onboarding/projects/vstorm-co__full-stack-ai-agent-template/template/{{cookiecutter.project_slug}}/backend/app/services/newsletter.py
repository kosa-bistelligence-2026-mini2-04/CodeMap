{%- if cookiecutter.enable_newsletter_signup %}
"""Newsletter service — accepts signups and triggers the welcome email."""

import logging
{%- if cookiecutter.enable_email %}

from app.services.email.service import get_email_service
{%- endif %}

logger = logging.getLogger(__name__)


class NewsletterService:
    """Business logic for newsletter signups.

    Holds no database session; current implementation only delegates to the email
    service. A future implementation may persist the subscription, push to a CRM, or
    enqueue a background job — adding those becomes a service-level change without the
    route having to learn about them.
    """

    def __init__(self) -> None:
{%- if cookiecutter.enable_email %}
        self._email = get_email_service()
{%- else %}
        pass
{%- endif %}

    async def subscribe(self, *, email: str, name: str | None = None) -> None:
        """Record a newsletter signup.

        The signup is treated as accepted even if the welcome email fails — the failure
        is logged so it can be diagnosed offline. This avoids returning 5xx to the user
        for a soft side-effect.
        """
        logger.info("newsletter_signup", extra={"email": email})
{%- if cookiecutter.enable_email %}
        try:
            await self._email.send_newsletter_welcome(to=email, name=name or email)
        except Exception:
            logger.exception("newsletter_welcome_email_failed", extra={"email": email})
{%- endif %}
{%- else %}
"""Newsletter service — not enabled."""
{%- endif %}
