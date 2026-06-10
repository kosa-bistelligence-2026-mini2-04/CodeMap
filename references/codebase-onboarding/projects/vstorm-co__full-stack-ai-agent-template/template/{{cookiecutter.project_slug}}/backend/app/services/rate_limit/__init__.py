{%- if cookiecutter.enable_rate_limiting %}
"""Per-plan, per-category sliding window rate limiting."""
{%- else %}
"""Rate limiting — not enabled."""
{%- endif %}
