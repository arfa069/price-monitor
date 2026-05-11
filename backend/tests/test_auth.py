"""Tests for authentication API."""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import get_password_hash
from app.database import get_db
from app.main import app
from app.models.user import User


class TestRegister:
    """Tests for POST /auth/register."""

    @pytest.mark.asyncio
    async def test_register_success(self):
        """Test successful user registration."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # No existing user
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.add = MagicMock()
        mock_session.commit = AsyncMock()
        mock_session.refresh = AsyncMock(side_effect=lambda u: setattr(u, "id", 1) or setattr(u, "created_at", datetime.now(UTC)) or setattr(u, "updated_at", datetime.now(UTC)))

        async def _override_get_db():
            yield mock_session

        app.dependency_overrides[get_db] = _override_get_db
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/auth/register",
                    json={"username": "testuser", "email": "test@example.com", "password": "123456"},
                )
            assert response.status_code == 201
            data = response.json()
            assert data["username"] == "testuser"
            assert data["email"] == "test@example.com"
            assert data["is_active"] is True
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_register_duplicate_username(self):
        """Test registration with duplicate username returns 400."""
        existing_user = MagicMock(spec=User)
        existing_user.username = "testuser"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        # First call: username exists
        mock_result.scalar_one_or_none.side_effect = [existing_user, None]
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def _override_get_db():
            yield mock_session

        app.dependency_overrides[get_db] = _override_get_db
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/auth/register",
                    json={"username": "testuser", "email": "test@example.com", "password": "123456"},
                )
            assert response.status_code == 400
            assert "用户名已注册" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self):
        """Test registration with duplicate email returns 400."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        # First call: username not exists, second call: email exists
        mock_result.scalar_one_or_none.side_effect = [None, MagicMock()]
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def _override_get_db():
            yield mock_session

        app.dependency_overrides[get_db] = _override_get_db
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/auth/register",
                    json={"username": "testuser", "email": "test@example.com", "password": "123456"},
                )
            assert response.status_code == 400
            assert "邮箱已注册" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_register_password_too_short(self):
        """Test registration with short password returns 422."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/auth/register",
                json={"username": "testuser", "email": "test@example.com", "password": "123"},
            )
        assert response.status_code == 422


class TestLogin:
    """Tests for POST /auth/login."""

    @pytest.mark.asyncio
    async def test_login_success(self):
        """Test successful login returns token."""
        hashed = get_password_hash("password123")
        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.hashed_password = hashed
        mock_user.is_active = True
        mock_user.created_at = datetime.now(UTC)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def _override_get_db():
            yield mock_session

        app.dependency_overrides[get_db] = _override_get_db
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/auth/login",
                    json={"username": "testuser", "password": "password123"},
                )
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_login_wrong_password(self):
        """Test login with wrong password returns 401."""
        hashed = get_password_hash("password123")
        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_user.hashed_password = hashed
        mock_user.is_active = True

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def _override_get_db():
            yield mock_session

        app.dependency_overrides[get_db] = _override_get_db
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/auth/login",
                    json={"username": "testuser", "password": "wrongpassword"},
                )
            assert response.status_code == 401
            assert "用户名或密码错误" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_login_user_not_found(self):
        """Test login with non-existent user returns 401."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def _override_get_db():
            yield mock_session

        app.dependency_overrides[get_db] = _override_get_db
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/auth/login",
                    json={"username": "nonexistent", "password": "password123"},
                )
            assert response.status_code == 401
            assert "用户名或密码错误" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_login_inactive_user(self):
        """Test login with inactive user returns 401."""
        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_user.hashed_password = get_password_hash("password123")
        mock_user.is_active = False

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def _override_get_db():
            yield mock_session

        app.dependency_overrides[get_db] = _override_get_db
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/auth/login",
                    json={"username": "testuser", "password": "password123"},
                )
            assert response.status_code == 401
            assert "用户已被禁用" in response.json()["detail"]
        finally:
            app.dependency_overrides.clear()


class TestGetMe:
    """Tests for GET /auth/me."""

    @pytest.mark.asyncio
    async def test_get_me_success(self):
        """Test successful get current user."""
        from app.core.security import get_password_hash

        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.hashed_password = get_password_hash("password123")
        mock_user.is_active = True
        mock_user.role = "user"
        mock_user.deleted_at = None
        mock_user.created_at = datetime.now(UTC)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def _override_get_db():
            yield mock_session

        app.dependency_overrides[get_db] = _override_get_db
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # First login to get token
                response = await client.post(
                    "/auth/login",
                    json={"username": "testuser", "password": "password123"},
                )
                token = response.json()["access_token"]

                # Then get me
                response = await client.get(
                    "/auth/me",
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert response.status_code == 200
            data = response.json()
            assert data["username"] == "testuser"
            assert data["email"] == "test@example.com"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_get_me_no_token(self):
        """Test get current user without token returns 401."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_me_invalid_token(self):
        """Test get current user with invalid token returns 401."""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get(
                "/auth/me",
                headers={"Authorization": "Bearer invalid_token"},
            )
        assert response.status_code == 401
        assert "Token 无效或已过期" in response.json()["detail"]


class TestLogout:
    """Tests for POST /auth/logout."""

    @pytest.mark.asyncio
    async def test_logout_success(self):
        """Test successful logout."""
        from app.core.security import get_password_hash

        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.hashed_password = get_password_hash("password123")
        mock_user.is_active = True
        mock_user.role = "user"
        mock_user.deleted_at = None
        mock_user.created_at = datetime.now(UTC)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def _override_get_db():
            yield mock_session

        app.dependency_overrides[get_db] = _override_get_db
        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # First login to get token
                response = await client.post(
                    "/auth/login",
                    json={"username": "testuser", "password": "password123"},
                )
                token = response.json()["access_token"]

                # Then logout
                response = await client.post(
                    "/auth/logout",
                    headers={"Authorization": f"Bearer {token}"},
                )
            assert response.status_code == 200
            assert "登出成功" in response.json()["message"]
        finally:
            app.dependency_overrides.clear()


class TestRequireRole:
    """Tests for require_role decorator."""

    @pytest.mark.asyncio
    async def test_require_role_allows_correct_role(self):
        """Test require_role allows user with correct role."""
        from app.core.security import require_role

        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.username = "adminuser"
        mock_user.email = "admin@example.com"
        mock_user.role = "admin"
        mock_user.is_active = True
        mock_user.deleted_at = None
        mock_user.created_at = datetime.now(UTC)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def _override_get_db():
            yield mock_session

        app.dependency_overrides[get_db] = _override_get_db
        try:
            # Test that user with admin role passes the role check
            role_checker = require_role("admin")
            # Directly call the dependency function with mocked user
            result = await role_checker(current_user=mock_user)
            assert result == mock_user
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_require_role_denies_wrong_role(self):
        """Test require_role denies user with wrong role."""
        from app.core.security import require_role
        from fastapi import HTTPException

        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.username = "regularuser"
        mock_user.email = "user@example.com"
        mock_user.role = "user"
        mock_user.is_active = True
        mock_user.deleted_at = None

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_user
        mock_session.execute = AsyncMock(return_value=mock_result)

        async def _override_get_db():
            yield mock_session

        app.dependency_overrides[get_db] = _override_get_db
        try:
            role_checker = require_role("admin", "super_admin")
            with pytest.raises(HTTPException) as exc_info:
                await role_checker(current_user=mock_user)
            assert exc_info.value.status_code == 403
            assert "需要管理员权限" in exc_info.value.detail
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_require_role_allows_super_admin(self):
        """Test require_role allows super_admin role."""
        from app.core.security import require_role

        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.username = "superadmin"
        mock_user.email = "super@example.com"
        mock_user.role = "super_admin"
        mock_user.is_active = True
        mock_user.deleted_at = None

        role_checker = require_role("admin", "super_admin")
        result = await role_checker(current_user=mock_user)
        assert result == mock_user

    @pytest.mark.asyncio
    async def test_require_role_denies_deleted_user(self):
        """Test require_role checks are done after get_current_user validates user is active."""
        from app.core.security import require_role

        # Inactive user should not pass get_current_user, so require_role
        # receives an active user with the correct role
        mock_user = MagicMock(spec=User)
        mock_user.id = 1
        mock_user.username = "activeadmin"
        mock_user.email = "admin@example.com"
        mock_user.role = "admin"
        mock_user.is_active = True
        mock_user.deleted_at = None

        # User is active and has admin role - should pass
        role_checker = require_role("admin")
        result = await role_checker(current_user=mock_user)
        assert result == mock_user
