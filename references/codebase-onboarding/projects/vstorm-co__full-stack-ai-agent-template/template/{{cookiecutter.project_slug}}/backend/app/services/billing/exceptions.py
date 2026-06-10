{%- if cookiecutter.enable_billing %}
"""Billing-specific domain exceptions."""

from app.core.exceptions import AppException


class BillingError(AppException):
    status_code = 400
    code = "BILLING_ERROR"


class StripeError(BillingError):
    status_code = 502
    code = "STRIPE_ERROR"


class StripeCardError(StripeError):
    status_code = 402
    code = "CARD_ERROR"


class InsufficientCreditsError(BillingError):
    status_code = 402
    code = "INSUFFICIENT_CREDITS"


class SubscriptionRequiredError(BillingError):
    status_code = 402
    code = "SUBSCRIPTION_REQUIRED"


class TrialIneligibleError(BillingError):
    status_code = 400
    code = "TRIAL_INELIGIBLE"


class InvalidWebhookError(BillingError):
    status_code = 400
    code = "INVALID_WEBHOOK"

{%- else %}
"""Billing exceptions — not enabled (enable_billing=false)."""
{%- endif %}
