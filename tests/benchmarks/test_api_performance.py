"""
API performance benchmarks using pytest-benchmark.
Run: pytest tests/benchmarks/ --benchmark-only
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

pytestmark = pytest.mark.asyncio


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.benchmark(min_rounds=10, max_time=2.0)
async def test_health_endpoint_performance(benchmark, client):
    async def _run():
        resp = await client.get("/health")
        return resp.status_code

    result = benchmark(_run)
    assert result == 200


@pytest.mark.benchmark(min_rounds=5, max_time=5.0)
async def test_history_endpoint_performance(benchmark, client):
    async def _run():
        resp = await client.get("/history?page=1&page_size=10")
        return resp.status_code

    result = benchmark(_run)
    assert result == 200


@pytest.mark.benchmark(min_rounds=5, max_time=5.0)
async def test_dashboard_endpoint_performance(benchmark, client):
    async def _run():
        resp = await client.get("/enterprise/dashboard")
        return resp.status_code

    result = benchmark(_run)
    assert result == 200


@pytest.mark.benchmark(min_rounds=5, max_time=10.0)
async def test_auth_flow_performance(benchmark, client):
    async def _run():
        resp = await client.post(
            "/auth/login",
            json={"email": "benchmark@test.com", "password": "Benchmark123"},
        )
        return resp.status_code

    result = benchmark(_run)
    assert result in (200, 401)
