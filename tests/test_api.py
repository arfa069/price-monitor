"""API tests for config, products pagination, and scheduler."""
import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from app.main import app


# --- Config Tests ---

@pytest.mark.asyncio
async def test_get_config_returns_crawl_cron_and_timezone():
    """GET /config returns crawl_cron and crawl_timezone fields."""
    from app.models.user import User
    from app.database import get_db

    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.username = "default"
    mock_user.feishu_webhook_url = "https://test"
    mock_user.crawl_frequency_hours = 1
    mock_user.data_retention_days = 365
    mock_user.crawl_cron = "0 9 * * *"
    mock_user.crawl_timezone = "Asia/Shanghai"
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
        assert data["crawl_cron"] == "0 9 * * *"
        assert data["crawl_timezone"] == "Asia/Shanghai"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_patch_config_invalid_cron_returns_422():
    """PATCH /config with invalid cron expression returns 422."""
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
            response = await client.patch("/config", json={"crawl_cron": "not-a-cron"})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_patch_config_invalid_timezone_returns_422():
    """PATCH /config with invalid timezone returns 422."""
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
                "/config",
                json={"crawl_cron": "0 9 * * *", "crawl_timezone": "Invalid/Zone"},
            )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_patch_config_valid_cron_rebuilds_scheduler_job():
    """PATCH /config with valid cron rebuilds the scheduler job."""
    from app.models.user import User
    from app.database import get_db

    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.username = "default"
    mock_user.feishu_webhook_url = ""
    mock_user.crawl_frequency_hours = 1
    mock_user.data_retention_days = 365
    mock_user.crawl_cron = None
    mock_user.crawl_timezone = "Asia/Shanghai"
    mock_user.created_at = None
    mock_user.updated_at = None

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    mock_scheduler = MagicMock()
    mock_scheduler.get_job.return_value = None
    mock_scheduler.add_job = MagicMock()

    async def _override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with patch("app.routers.config._get_scheduler", return_value=mock_scheduler):
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.patch(
                    "/config",
                    json={"crawl_cron": "0 9 * * *", "crawl_timezone": "Asia/Shanghai"},
                )
        assert response.status_code == 200
        data = response.json()
        assert data["crawl_cron"] == "0 9 * * *"
        mock_scheduler.add_job.assert_called_once()
        call_kwargs = mock_scheduler.add_job.call_args.kwargs
        assert call_kwargs["id"] == "crawl_cron_job"
        assert call_kwargs["max_instances"] == 1
    finally:
        app.dependency_overrides.clear()


# --- Products Pagination Tests ---


@pytest.mark.asyncio
async def test_products_list_returns_pagination_metadata():
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
async def test_products_list_page_out_of_range_returns_empty_items():
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
async def test_products_list_first_page_has_no_prev():
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
    """GET /scheduler/status returns 503 when scheduler not initialized."""
    # Patch app.state to have no scheduler
    mock_state = MagicMock()
    mock_state.scheduler = None

    with patch.object(app, "state", mock_state):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/scheduler/status")
    assert response.status_code == 503
    data = response.json()
    assert data["scheduler"] == "not_started"


# --- Health Check ---


@pytest.mark.asyncio
async def test_health_check_includes_scheduler_field():
    """Health endpoint includes scheduler field in checks."""
    mock_state = MagicMock()
    mock_state.scheduler = None

    with patch.object(app, "state", mock_state):
        with patch("app.main.engine") as mock_engine:
            mock_conn = MagicMock()
            mock_conn.execute = AsyncMock()
            mock_engine.connect.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
            mock_engine.connect.return_value.__aexit__ = AsyncMock()

            with patch("app.main.redis") as _mock_redis:
                mock_redis = AsyncMock()
                mock_redis.from_url.return_value = mock_redis
                mock_redis.ping = AsyncMock()
                mock_redis.aclose = AsyncMock()

                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "scheduler" in data["checks"]
    assert data["checks"]["scheduler"] == "not_running"
