"""API tests for config, products pagination, and scheduler."""
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import get_current_user
from app.main import app
from app.models.user import User


def create_mock_user(user_id=1, username="testuser", role="user"):
    """Create a mock user with minimal attributes."""
    user = MagicMock()
    user.id = user_id
    user.username = username
    user.email = f"{username}@example.com"
    user.role = role
    user.deleted_at = None
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    return user


@pytest.fixture
def mock_get_current_user():
    """Mock get_current_user to return a test user."""
    async def _mock_get_current_user(token=None, db=None):
        return create_mock_user()
    app.dependency_overrides[get_current_user] = _mock_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


# --- Config Tests ---

@pytest.mark.asyncio
async def test_get_config_returns_user_config():
    """GET /config returns user configuration."""
    from app.database import get_db

    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.username = "default"
    mock_user.feishu_webhook_url = "https://test"
    mock_user.data_retention_days = 365
    mock_user.created_at = None
    mock_user.updated_at = None

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def _override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/config")
        assert response.status_code == 200
        data = response.json()
        assert data["feishu_webhook_url"] == "https://test"
        assert data["data_retention_days"] == 365
    finally:
        app.dependency_overrides.clear()


# --- URL Validation Tests ---


@pytest.mark.asyncio
async def test_create_product_rejects_invalid_url_no_scheme(mock_get_current_user):
    """POST /products rejects URLs without http/https scheme."""
    from app.database import get_db

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def _override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Test "not-a-url" - no scheme
            response = await client.post(
                "/products",
                json={"platform": "jd", "url": "not-a-url"},
            )
            assert response.status_code == 422
            assert "URL must start with" in response.json()["detail"][0]["msg"]
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_product_rejects_ftp_scheme(mock_get_current_user):
    """POST /products rejects ftp:// URLs."""
    from app.database import get_db

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def _override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/products",
                json={"platform": "jd", "url": "ftp://example.com/item"},
            )
            assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_update_product_rejects_empty_url(mock_get_current_user):
    """PATCH /products rejects empty string URL."""
    from app.database import get_db

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def _override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/products/1",
                json={"url": ""},
            )
            assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_product_strips_whitespace(mock_get_current_user):
    """POST /products strips whitespace from URL before saving."""
    from app.database import get_db

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.refresh = AsyncMock(side_effect=lambda p: setattr(p, "id", 1) or setattr(p, "created_at", datetime.now(UTC)) or setattr(p, "updated_at", datetime.now(UTC)))

    async def _override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/products",
                json={"platform": "jd", "url": "  https://item.jd.com/123  "},
            )
            assert response.status_code == 200
            # Verify the URL was stripped
            call_args = mock_session.add.call_args[0][0]
            assert call_args.url == "https://item.jd.com/123"
    finally:
        app.dependency_overrides.clear()


# --- Products Pagination Tests ---


@pytest.mark.asyncio
async def test_products_list_returns_pagination_metadata(mock_get_current_user):
    """GET /products returns page, page_size, total_pages, has_next, has_prev."""
    from app.database import get_db

    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 30

    mock_items_result = MagicMock()
    mock_items_result.scalars.return_value.all.return_value = []

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=[mock_count_result, mock_items_result])

    async def _override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/products?page=2&size=15")
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 2
        assert data["page_size"] == 15
        assert data["total_pages"] == 2
        assert data["has_next"] is False
        assert data["has_prev"] is True
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_products_list_page_out_of_range_returns_empty_items(mock_get_current_user):
    """GET /products with page beyond total returns empty items with valid metadata."""
    from app.database import get_db

    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 10

    mock_items_result = MagicMock()
    mock_items_result.scalars.return_value.all.return_value = []

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=[mock_count_result, mock_items_result])

    async def _override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/products?page=100")
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 10
        assert data["page"] == 100
        assert data["total_pages"] == 1
        assert data["has_next"] is False
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_products_list_first_page_has_no_prev(mock_get_current_user):
    """GET /products page=1 has has_prev=False."""
    from app.database import get_db

    mock_count_result = MagicMock()
    mock_count_result.scalar.return_value = 20

    mock_items_result = MagicMock()
    mock_items_result.scalars.return_value.all.return_value = []

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=[mock_count_result, mock_items_result])

    async def _override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/products?page=1&size=15")
        data = response.json()
        assert data["page"] == 1
        assert data["has_prev"] is False
        assert data["has_next"] is True
    finally:
        app.dependency_overrides.clear()


# --- Scheduler Status Endpoint Tests ---


@pytest.mark.asyncio
async def test_scheduler_status_returns_503_when_not_started():
    """GET /scheduler/status returns 503 when scheduler not initialized (admin only)."""
    # Patch app.state to have no scheduler
    mock_state = MagicMock()
    mock_state.scheduler = None

    async def _admin():
        return create_mock_user(role="admin")
    app.dependency_overrides[get_current_user] = _admin

    try:
        with patch.object(app, "state", mock_state):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/scheduler/status",
                    headers={"Authorization": "Bearer fake"},
                )
        assert response.status_code == 503
        data = response.json()
        assert data["scheduler"] == "not_started"
    finally:
        app.dependency_overrides.pop(get_current_user, None)


# --- Health Check ---


# test_health_check_includes_scheduler_field removed:
# /health is now redacted to only return {"status": "healthy"|"unhealthy"}.
# Coverage for the new shape lives in tests/test_health_endpoint.py.


