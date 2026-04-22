"""API smoke tests."""
import pytest
from unittest.mock import patch
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    """Health endpoint returns 200."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("healthy", "unhealthy")
    assert "checks" in data


@pytest.mark.asyncio
async def test_crawl_trigger_returns_200():
    """Crawl trigger endpoint returns 200 without actually crawling."""
    with patch("app.routers.crawl.get_active_products", return_value=[]):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/crawl/crawl-now")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "no_products"
