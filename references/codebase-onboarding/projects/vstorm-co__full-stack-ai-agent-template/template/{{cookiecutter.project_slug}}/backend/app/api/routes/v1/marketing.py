{%- if cookiecutter.enable_newsletter_signup %}
"""Marketing routes — newsletter signup."""

from typing import Any

from fastapi import APIRouter, status

from app.api.deps import NewsletterSvc
from app.schemas.marketing import NewsletterSignupCreate, NewsletterSignupRead

router = APIRouter()


@router.post(
    "/newsletter/signup",
    response_model=NewsletterSignupRead,
    status_code=status.HTTP_201_CREATED,
)
async def newsletter_signup(
    data: NewsletterSignupCreate,
    service: NewsletterSvc,
) -> Any:
    """Subscribe an email to the newsletter."""
    await service.subscribe(email=data.email, name=data.name)
    return NewsletterSignupRead(email=data.email)
{%- else %}
"""Marketing routes — not enabled."""
{%- endif %}
