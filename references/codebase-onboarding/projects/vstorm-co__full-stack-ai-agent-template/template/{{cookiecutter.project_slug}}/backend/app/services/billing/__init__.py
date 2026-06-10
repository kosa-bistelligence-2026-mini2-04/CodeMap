{%- if cookiecutter.enable_billing %}
"""Billing domain — facade + Stripe integration + handlers + sub-services.

External callers should import only ``BillingService`` from this package; the
sub-services (checkout, credits, subscription, webhook) are package-internal.
"""

from app.services.billing.facade import BillingService

__all__ = ["BillingService"]
{%- else %}
"""Billing module — not enabled (enable_billing=false)."""
{%- endif %}
