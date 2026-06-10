{%- if cookiecutter.enable_newsletter_signup %}
"""Marketing schemas — newsletter signup."""

from pydantic import EmailStr, Field

from app.schemas.base import BaseSchema


class NewsletterSignupCreate(BaseSchema):
    """Request body for subscribing to the newsletter."""

    email: EmailStr = Field(..., description="Email address to subscribe")
    name: str | None = Field(default=None, max_length=255)


class NewsletterSignupRead(BaseSchema):
    """Response after a successful subscription."""

    email: EmailStr
    message: str = "Subscribed successfully"
{%- else %}
"""Marketing schemas — not enabled."""
{%- endif %}
