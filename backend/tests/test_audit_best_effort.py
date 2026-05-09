"""Best-effort audit logging behavior tests."""
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import get_current_user
from app.database import get_db
from app.main import app


def create_mock_user(user_id: int = 1, username: str = "testuser", role: str = "user"):
    """Create a mock authenticated user."""
    user = MagicMock()
    user.id = user_id
    user.username = username
    user.email = f"{username}@example.com"
    user.role = role
    user.deleted_at = None
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    return user


def create_mock_product(product_id: int = 1, user_id: int = 1):
    """Create a mock product row."""
    product = MagicMock()
    product.id = product_id
    product.user_id = user_id
    product.platform = "jd"
    product.url = "https://item.jd.com/123.html"
    product.title = "Test Product"
    product.active = True
    product.created_at = datetime.now(UTC)
    product.updated_at = datetime.now(UTC)
    return product


def create_mock_job_config(config_id: int = 1, user_id: int = 1, name: str = "Config A"):
    """Create a mock job search config row."""
    return SimpleNamespace(
        id=config_id,
        user_id=user_id,
        name=name,
        keyword=None,
        city_code=None,
        salary_min=None,
        salary_max=None,
        experience=None,
        education=None,
        url="https://www.zhipin.com/job_detail/?query=python",
        active=True,
        notify_on_new=True,
        deactivation_threshold=3,
        cron_expression=None,
        cron_timezone="Asia/Shanghai",
        enable_match_analysis=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.fixture(autouse=True)
def cleanup_overrides():
    """Reset FastAPI dependency overrides for each test."""
    yield
    app.dependency_overrides.clear()


def setup_overrides(user, db_session):
    """Install dependency overrides for auth and db."""
    async def _mock_get_current_user(token=None, db=None):
        return user

    async def _mock_get_db():
        yield db_session

    app.dependency_overrides[get_current_user] = _mock_get_current_user
    app.dependency_overrides[get_db] = _mock_get_db


@pytest.mark.asyncio
async def test_delete_product_audit_success_path_calls_log_audit():
    """Business deletion succeeds and audit logger is invoked."""
    current_user = create_mock_user()
    product = create_mock_product(product_id=11, user_id=current_user.id)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = product

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()

    setup_overrides(current_user, mock_db)

    with patch("app.routers.products.log_audit", new=AsyncMock(return_value=MagicMock())) as mock_log_audit:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/products/11")

    assert response.status_code == 200
    assert response.json()["message"] == "Product deleted"
    mock_db.delete.assert_awaited_once_with(product)
    mock_db.commit.assert_awaited_once()
    mock_log_audit.assert_awaited_once()
    _, kwargs = mock_log_audit.await_args
    assert kwargs["action"] == "product.delete"
    assert kwargs["actor_user_id"] == current_user.id
    assert kwargs["target_id"] == 11
    assert kwargs["commit"] is True


@pytest.mark.asyncio
async def test_delete_product_audit_failure_does_not_break_business_success():
    """Audit write failure (best effort) must not fail the delete API."""
    current_user = create_mock_user()
    product = create_mock_product(product_id=22, user_id=current_user.id)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = product

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()

    setup_overrides(current_user, mock_db)

    # Simulate best-effort audit path: logger returns None instead of raising.
    with patch("app.routers.products.log_audit", new=AsyncMock(return_value=None)):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/products/22")

    assert response.status_code == 200
    assert response.json()["message"] == "Product deleted"
    mock_db.delete.assert_awaited_once_with(product)
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_create_job_config_audit_success_path_calls_log_audit():
    """Job config creation succeeds and audit logger is invoked."""
    current_user = create_mock_user()

    mock_db = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    async def _refresh_side_effect(obj):
        obj.id = 101
        obj.created_at = datetime.now(UTC)
        obj.updated_at = datetime.now(UTC)
        obj.user_id = current_user.id
        if obj.cron_timezone is None:
            obj.cron_timezone = "Asia/Shanghai"
        if obj.enable_match_analysis is None:
            obj.enable_match_analysis = False

    mock_db.refresh = AsyncMock(side_effect=_refresh_side_effect)
    setup_overrides(current_user, mock_db)

    with patch("app.routers.jobs.log_audit", new=AsyncMock(return_value=MagicMock())) as mock_log_audit:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/jobs/configs",
                json={
                    "name": "My Config",
                    "url": "https://www.zhipin.com/job_detail/?query=python",
                },
            )

    assert response.status_code == 201
    assert response.json()["id"] == 101
    mock_db.commit.assert_awaited_once()
    mock_log_audit.assert_awaited_once()
    _, kwargs = mock_log_audit.await_args
    assert kwargs["action"] == "job_config.create"
    assert kwargs["actor_user_id"] == current_user.id
    assert kwargs["target_id"] == 101
    assert kwargs["commit"] is True


@pytest.mark.asyncio
async def test_update_job_config_audit_failure_does_not_break_business_success():
    """Audit write failure (best effort) must not fail the update API."""
    current_user = create_mock_user()
    config = create_mock_job_config(config_id=202, user_id=current_user.id, name="Before Update")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = config

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    setup_overrides(current_user, mock_db)

    with patch("app.routers.jobs.log_audit", new=AsyncMock(return_value=None)):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/jobs/configs/202",
                json={"name": "After Update"},
            )

    assert response.status_code == 200
    assert response.json()["id"] == 202
    assert response.json()["name"] == "After Update"
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_delete_job_config_audit_success_path_calls_log_audit():
    """Job config deletion succeeds and audit logger is invoked."""
    current_user = create_mock_user()
    config = create_mock_job_config(config_id=303, user_id=current_user.id, name="Delete Me")

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = config

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()
    setup_overrides(current_user, mock_db)

    with patch("app.routers.jobs.log_audit", new=AsyncMock(return_value=MagicMock())) as mock_log_audit:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/jobs/configs/303")

    assert response.status_code == 200
    assert response.json()["message"] == "Config deleted"
    mock_db.delete.assert_awaited_once_with(config)
    mock_db.commit.assert_awaited_once()
    mock_log_audit.assert_awaited_once()
    _, kwargs = mock_log_audit.await_args
    assert kwargs["action"] == "job_config.delete"
    assert kwargs["actor_user_id"] == current_user.id
    assert kwargs["target_id"] == 303
    assert kwargs["commit"] is True


@pytest.mark.asyncio
async def test_login_audit_failure_does_not_break_business_success():
    """Audit write failure must not fail successful login."""
    current_user = create_mock_user(user_id=404, username="loginuser")
    current_user.hashed_password = "hashed-value"
    current_user.is_active = True

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = current_user

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    setup_overrides(current_user, mock_db)

    with (
        patch("app.api.auth.is_account_locked", new=AsyncMock(return_value=(False, 0))),
        patch("app.api.auth.verify_password", return_value=True),
        patch("app.api.auth.clear_login_attempts", new=AsyncMock()),
        patch("app.api.auth.create_access_token", return_value="token-abc"),
        patch("app.api.auth.create_session", new=AsyncMock()),
        patch("app.api.auth.log_audit", new=AsyncMock(return_value=None)),
    ):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/auth/login",
                json={"username": "loginuser", "password": "password123"},
            )

    assert response.status_code == 200
    assert response.json()["access_token"] == "token-abc"
    mock_db.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_logout_audit_failure_does_not_break_business_success():
    """Audit write failure must not fail logout."""
    current_user = create_mock_user(user_id=505, username="logoutuser")

    mock_db = AsyncMock()
    setup_overrides(current_user, mock_db)

    with patch("app.api.auth.log_audit", new=AsyncMock(return_value=None)):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/auth/logout")

    assert response.status_code == 200
    assert response.json()["message"] == "登出成功"
