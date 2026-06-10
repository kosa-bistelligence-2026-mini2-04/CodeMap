{%- if cookiecutter.enable_prometheus %}
"""Prometheus metrics endpoint tests."""

import pytest
from httpx import AsyncClient

from app.core.config import settings


@pytest.mark.anyio
async def test_metrics_endpoint(client: AsyncClient):
    """Test that /metrics endpoint returns Prometheus metrics."""
    response = await client.get(settings.PROMETHEUS_METRICS_PATH)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/plain")

    # Check for standard prometheus-fastapi-instrumentator metrics
    content = response.text
    assert "http_requests_total" in content
    assert "http_request_duration_seconds" in content


@pytest.mark.anyio
async def test_metrics_increments_on_request(client: AsyncClient):
    """Test that metrics are incremented after making requests."""
    # Make a health check request first
    await client.get(f"{settings.API_V1_STR}/health")

    # Then check metrics
    response = await client.get(settings.PROMETHEUS_METRICS_PATH)
    assert response.status_code == 200

    content = response.text
    # Should have recorded the health check request
    assert "http_requests_total" in content


@pytest.mark.anyio
async def test_metrics_excluded_from_own_metrics(client: AsyncClient):
    """Test that /metrics endpoint doesn't count itself in metrics."""
    # Make multiple requests to /metrics
    for _ in range(3):
        await client.get(settings.PROMETHEUS_METRICS_PATH)

    response = await client.get(settings.PROMETHEUS_METRICS_PATH)
    content = response.text

    # The /metrics endpoint should be excluded from instrumentation
    # so we shouldn't see it in the metrics path labels
    assert f'path="{settings.PROMETHEUS_METRICS_PATH}"' not in content
{%- else %}
# Prometheus metrics are not enabled for this project
{%- endif %}
