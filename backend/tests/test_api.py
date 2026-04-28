"""API tests for config, products pagination, and scheduler."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app

# --- Config Tests ---

@pytest.mark.asyncio
async def test_get_config_returns_crawl_cron_and_timezone():
    """GET /config returns crawl_cron and crawl_timezone fields."""
    from app.database import get_db
    from app.models.user import User

    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.username = "default"
    mock_user.feishu_webhook_url = "https://test"
    mock_user.crawl_frequency_hours = 1
    mock_user.data_retention_days = 365
    mock_user.crawl_cron = "0 9 * * *"
    mock_user.crawl_timezone = "Asia/Shanghai"
    mock_user.job_crawl_cron = None
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
    from app.database import get_db
    from app.models.user import User

    mock_user = MagicMock(spec=User)
    mock_user.id = 1
    mock_user.username = "default"
    mock_user.feishu_webhook_url = ""
    mock_user.crawl_frequency_hours = 1
    mock_user.data_retention_days = 365
    mock_user.crawl_cron = None
    mock_user.crawl_timezone = "Asia/Shanghai"
    mock_user.job_crawl_cron = None
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


# --- URL Validation Tests ---


@pytest.mark.asyncio
async def test_create_product_rejects_invalid_url_no_scheme():
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
async def test_create_product_rejects_ftp_scheme():
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
async def test_update_product_rejects_empty_url():
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
async def test_create_product_strips_whitespace():
    """POST /products strips whitespace from URL before saving."""
    from datetime import UTC, datetime

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


# --- Job Crawl Cron Tests ---


@pytest.mark.asyncio
async def test_get_job_crawl_cron_returns_default():
    """GET /config/job-crawl-cron returns job_crawl_cron from DB or default."""
    from app.database import get_db
    from app.models.user import User

    mock_user = MagicMock(spec=User)
    mock_user.job_crawl_cron = "0 9 * * *"
    mock_user.crawl_timezone = "Asia/Shanghai"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user

    mock_db = MagicMock()
    mock_db.execute = AsyncMock(return_value=mock_result)

    async def _override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get("/config/job-crawl-cron")
        assert resp.status_code == 200
        assert "job_crawl_cron" in resp.json()
        assert resp.json()["default"] == "0 9 * * *"
    finally:
        app.dependency_overrides.clear()
