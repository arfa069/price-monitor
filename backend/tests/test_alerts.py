"""Tests for alerts router."""
from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import get_current_user
from app.database import get_db
from app.main import app


@pytest.fixture
def mock_db_session():
    """Mock database session for alert tests."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def mock_get_db(mock_db_session):
    """Override get_db dependency with mock session."""
    async def _override():
        yield mock_db_session
    app.dependency_overrides[get_db] = _override
    yield mock_db_session
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def mock_current_user():
    """Override get_current_user dependency."""
    user = MagicMock()
    user.id = 1
    user.username = "testuser"
    user.email = "test@example.com"

    async def _override():
        return user
    app.dependency_overrides[get_current_user] = _override
    yield user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def mock_product():
    """Mock product for alert tests."""
    product = MagicMock()
    product.id = 1
    product.user_id = 1
    product.name = "Test Product"
    return product


@pytest.fixture
def mock_alert():
    """Mock alert for alert tests."""
    alert = MagicMock()
    alert.id = 1
    alert.product_id = 1
    alert.alert_type = "price_drop"
    alert.threshold_percent = Decimal("5.00")
    alert.last_notified_at = None
    alert.last_notified_price = None
    alert.active = True
    alert.created_at = datetime.now(UTC)
    alert.updated_at = datetime.now(UTC)
    return alert


# --- POST /alerts Tests ---


@pytest.mark.asyncio
async def test_create_alert_success(mock_get_db, mock_current_user, mock_product, mock_alert):
    """POST /alerts with valid data returns 201."""
    mock_alert.id = 1

    def mock_refresh(a):
        a.id = 1
        a.created_at = datetime.now(UTC)
        a.updated_at = datetime.now(UTC)
    mock_get_db.refresh.side_effect = mock_refresh

    # First call: product exists
    product_result = MagicMock()
    product_result.scalar_one_or_none.return_value = mock_product
    mock_get_db.execute.return_value = product_result

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/alerts",
            json={"product_id": 1, "threshold_percent": "5.00", "active": True},
        )

    assert response.status_code == 201
    data = response.json()
    assert data["product_id"] == 1
    assert data["threshold_percent"] == "5.00"
    assert data["active"] is True


@pytest.mark.asyncio
async def test_create_alert_product_not_found(mock_get_db, mock_current_user):
    """POST /alerts with non-existent product returns 404."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_get_db.execute.return_value = result

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/alerts",
            json={"product_id": 999, "threshold_percent": "5.00", "active": True},
        )

    assert response.status_code == 404
    assert "not found" in response.json().get("detail", "").lower()


# --- GET /alerts Tests ---


@pytest.mark.asyncio
async def test_list_alerts_success(mock_get_db, mock_current_user, mock_alert):
    """GET /alerts returns list of alerts."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = [mock_alert]
    mock_get_db.execute.return_value = result

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/alerts")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == 1


@pytest.mark.asyncio
async def test_list_alerts_with_product_filter(mock_get_db, mock_current_user, mock_alert):
    """GET /alerts?product_id=1 filters by product."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = [mock_alert]
    mock_get_db.execute.return_value = result

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/alerts?product_id=1")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


@pytest.mark.asyncio
async def test_list_alerts_with_active_filter(mock_get_db, mock_current_user, mock_alert):
    """GET /alerts?active=true filters by active status."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = [mock_alert]
    mock_get_db.execute.return_value = result

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/alerts?active=true")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1


# --- GET /alerts/{id} Tests ---


@pytest.mark.asyncio
async def test_get_alert_success(mock_get_db, mock_current_user, mock_alert):
    """GET /alerts/1 returns alert details."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_alert
    mock_get_db.execute.return_value = result

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/alerts/1")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1
    assert data["alert_type"] == "price_drop"


@pytest.mark.asyncio
async def test_get_alert_not_found(mock_get_db, mock_current_user):
    """GET /alerts/999 returns 404."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_get_db.execute.return_value = result

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/alerts/999")

    assert response.status_code == 404
    assert "not found" in response.json().get("detail", "").lower()


# --- PATCH /alerts/{id} Tests ---


@pytest.mark.asyncio
async def test_update_alert_success(mock_get_db, mock_current_user, mock_alert):
    """PATCH /alerts/1 updates alert."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_alert
    mock_get_db.execute.return_value = result

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            "/alerts/1",
            json={"threshold_percent": "10.00", "active": False},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == 1


@pytest.mark.asyncio
async def test_update_alert_not_found(mock_get_db, mock_current_user):
    """PATCH /alerts/999 returns 404."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_get_db.execute.return_value = result

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            "/alerts/999",
            json={"threshold_percent": "10.00"},
        )

    assert response.status_code == 404


# --- DELETE /alerts/{id} Tests ---


@pytest.mark.asyncio
async def test_delete_alert_success(mock_get_db, mock_current_user, mock_alert):
    """DELETE /alerts/1 deletes alert."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = mock_alert
    mock_get_db.execute.return_value = result

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete("/alerts/1")

    assert response.status_code == 200
    assert "deleted" in response.json().get("message", "").lower()


@pytest.mark.asyncio
async def test_delete_alert_not_found(mock_get_db, mock_current_user):
    """DELETE /alerts/999 returns 404."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = None
    mock_get_db.execute.return_value = result

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.delete("/alerts/999")

    assert response.status_code == 404
