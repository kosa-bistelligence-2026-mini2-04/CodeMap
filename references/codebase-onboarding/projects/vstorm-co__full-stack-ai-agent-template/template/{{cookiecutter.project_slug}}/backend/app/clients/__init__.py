"""External service clients.

This module contains thin wrappers around external services like Redis.
"""
{%- if cookiecutter.enable_redis %}

from app.clients.redis import RedisClient
{%- endif %}

__all__ = [
{%- if cookiecutter.enable_redis %}
    "RedisClient",
{%- endif %}
]
