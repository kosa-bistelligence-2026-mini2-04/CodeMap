{%- if cookiecutter.enable_billing %}
"""Webhook event handlers — one module per Stripe event family."""
{%- else %}
"""Webhook handlers — not enabled (enable_billing=false)."""
{%- endif %}
