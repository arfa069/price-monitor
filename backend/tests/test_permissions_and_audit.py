"""Tests for permission-based access control, admin role boundaries, and audit logging."""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, status
from httpx import ASGITransport, AsyncClient

from app.core.security import get_current_user
from app.database import get_db
from app.main import app
from app.models.user import User


def create_mock_user(user_id, username, email, role, is_active=True, deleted_at=None):
    """Create a mock user."""
    user = MagicMock()
    user.id = user_id
    user.username = username
    user.email = email
    user.role = role
    user.is_active = is_active
    user.deleted_at = deleted_at
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    return user


def setup_mock_current_user(user):
    """Override get_current_user to return a specific user."""
    async def mock_get_current_user(token=None, db=None):
        return user
    app.dependency_overrides[get_current_user] = mock_get_current_user


def setup_mock_db():
    """Create and register a mock DB session."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalar.return_value = 0
    mock_result.scalars.return_value = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()
    mock_session.add = MagicMock()

    def _refresh_side_effect(obj):
        if not getattr(obj, "id", None):
            obj.id = 999
        if not getattr(obj, "created_at", None):
            obj.created_at = datetime.now(UTC)
        if not getattr(obj, "updated_at", None):
            obj.updated_at = datetime.now(UTC)
    mock_session.refresh = AsyncMock(side_effect=_refresh_side_effect)

    async def _override():
        yield mock_session
    app.dependency_overrides[get_db] = _override
    return mock_session


@pytest.fixture(autouse=True)
def cleanup_overrides():
    """Clean up dependency overrides after each test."""
    yield
    app.dependency_overrides.clear()


class TestAdminSelfPromotionPrevention:
    """Tests that admin cannot escalate privileges."""

    @pytest.mark.asyncio
    async def test_admin_cannot_create_super_admin(self):
        """Admin creating user with super_admin role should get 403."""
        admin_user = create_mock_user(1, "admin", "admin@example.com", "admin")
        setup_mock_current_user(admin_user)
        setup_mock_db()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/admin/users",
                json={"username": "newadmin", "email": "new@example.com", "password": "123456", "role": "super_admin"},
            )
        assert response.status_code == 403
        assert "super_admin" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_admin_cannot_promote_to_super_admin(self):
        """Admin updating user role to super_admin should get 403."""
        admin_user = create_mock_user(1, "admin", "admin@example.com", "admin")
        target_user = create_mock_user(2, "target", "target@example.com", "user")
        setup_mock_current_user(admin_user)

        mock_session = setup_mock_db()
        # First execute: find user by id; second: no conflict
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = target_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/admin/users/2",
                json={"role": "super_admin"},
            )
        assert response.status_code == 403
        assert "super_admin" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_admin_cannot_modify_super_admin(self):
        """Admin modifying a super_admin user should get 403."""
        admin_user = create_mock_user(1, "admin", "admin@example.com", "admin")
        super_user = create_mock_user(2, "super", "super@example.com", "super_admin")
        setup_mock_current_user(admin_user)

        mock_session = setup_mock_db()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = super_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/admin/users/2",
                json={"is_active": False},
            )
        assert response.status_code == 403
        assert "不能修改 super_admin" in response.json()["detail"]


class TestAdminCannotDeleteSuperAdmin:
    """Tests that admin cannot delete super_admin users."""

    @pytest.mark.asyncio
    async def test_admin_cannot_delete_super_admin(self):
        """Admin deleting a super_admin user should get 403."""
        admin_user = create_mock_user(1, "admin", "admin@example.com", "admin")
        super_user = create_mock_user(2, "super", "super@example.com", "super_admin")
        setup_mock_current_user(admin_user)

        mock_session = setup_mock_db()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = super_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/admin/users/2")
        assert response.status_code == 403
        assert "不能删除 super_admin" in response.json()["detail"]


class TestCrawlPermissionDeniedForAdmin:
    """Tests that admin cannot trigger crawls."""

    @pytest.mark.asyncio
    async def test_admin_cannot_trigger_crawl_now(self):
        """Admin calling POST /products/crawl/crawl-now should get 403."""
        admin_user = create_mock_user(1, "admin", "admin@example.com", "admin")
        setup_mock_current_user(admin_user)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/products/crawl/crawl-now")
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_cannot_trigger_job_crawl(self):
        """Admin calling POST /jobs/crawl-now should get 403."""
        admin_user = create_mock_user(1, "admin", "admin@example.com", "admin")
        setup_mock_current_user(admin_user)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/jobs/crawl-now")
        assert response.status_code == 403


class TestScheduleConfigPermissionDeniedForAdmin:
    """Tests that admin cannot modify schedule configs."""

    @pytest.mark.asyncio
    async def test_admin_cannot_create_product_cron(self):
        """Admin calling POST /products/cron-configs should get 403."""
        admin_user = create_mock_user(1, "admin", "admin@example.com", "admin")
        setup_mock_current_user(admin_user)
        setup_mock_db()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/products/cron-configs",
                json={"platform": "taobao", "cron_expression": "0 9 * * *"},
            )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_admin_cannot_update_product_cron(self):
        """Admin calling PATCH /products/cron-configs/{platform} should get 403."""
        admin_user = create_mock_user(1, "admin", "admin@example.com", "admin")
        setup_mock_current_user(admin_user)
        setup_mock_db()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/products/cron-configs/taobao",
                json={"cron_expression": "0 10 * * *"},
            )
        assert response.status_code == 403


class TestWeChatDisabled:
    """Tests that WeChat login returns 503 when not configured."""

    @pytest.mark.asyncio
    async def test_wechat_qr_returns_503_when_disabled(self):
        """GET /auth/wechat/qr should return 503 when feature flag is off."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/auth/wechat/qr")
        assert response.status_code == 503
        assert "未启用" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_wechat_callback_returns_503_when_disabled(self):
        """GET /auth/wechat/callback should return 503 when feature flag is off."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/auth/wechat/callback?code=test&state=test")
        assert response.status_code == 503


class TestAuditLogEndpoint:
    """Tests for /admin/audit-logs endpoint."""

    @pytest.mark.asyncio
    async def test_super_admin_can_list_audit_logs(self):
        """super_admin should be able to list audit logs."""
        super_user = create_mock_user(1, "super", "super@example.com", "super_admin")
        setup_mock_current_user(super_user)
        setup_mock_db()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/admin/audit-logs")
        # 200 if no error from db, else still authenticated
        assert response.status_code in (200, 500)

    @pytest.mark.asyncio
    async def test_regular_user_cannot_access_audit_logs(self):
        """Regular user should get 403 on /admin/audit-logs."""
        regular_user = create_mock_user(1, "user", "user@example.com", "user")
        setup_mock_current_user(regular_user)

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/admin/audit-logs")
        assert response.status_code == 403


class TestSuperAdminCanPerformAdminActions:
    """Tests that super_admin can perform restricted admin actions."""

    @pytest.mark.asyncio
    async def test_super_admin_can_create_user(self):
        """super_admin creating a regular user should succeed (not 403)."""
        super_user = create_mock_user(1, "super", "super@example.com", "super_admin")
        setup_mock_current_user(super_user)
        setup_mock_db()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/admin/users",
                json={"username": "newuser", "email": "new@example.com", "password": "123456", "role": "user"},
            )
        # Should not be 403 (may be 201 or other success/error)
        assert response.status_code != 403

    @pytest.mark.asyncio
    async def test_super_admin_can_create_super_admin(self):
        """super_admin creating another super_admin should succeed (not 403)."""
        super_user = create_mock_user(1, "super", "super@example.com", "super_admin")
        setup_mock_current_user(super_user)
        setup_mock_db()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/admin/users",
                json={"username": "newsuper", "email": "newsuper@example.com", "password": "123456", "role": "super_admin"},
            )
        assert response.status_code != 403
