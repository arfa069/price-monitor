"""API smoke tests."""
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_health_check():
    """Health endpoint returns 200."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_product_list_empty():
    """Products list returns empty array when no products."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/products")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_alerts_list_empty():
    """Alerts list returns empty array when no alerts."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/alerts")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_config_returns_defaults():
    """Config endpoint returns system configuration."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/config")
    assert response.status_code == 200
    data = response.json()
    assert "crawl_frequency_hours" in data
    assert "data_retention_days" in data
    assert data["crawl_frequency_hours"] == 1
    assert data["data_retention_days"] == 365


@pytest.mark.asyncio
async def test_crawl_trigger_returns_202():
    """Crawl trigger endpoint accepts crawl requests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/crawl/trigger")
    assert response.status_code == 202
