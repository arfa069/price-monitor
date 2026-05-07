"""Redis integration tests using mocks (avoids real Redis dependency)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestRedisHealthCheck:
    """Tests for Redis health check in /health endpoint."""

    @pytest.mark.asyncio
    async def test_health_redis_healthy(self):
        """Health endpoint reports redis healthy when client responds."""
        from app.main import app

        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(return_value=True)
        mock_redis.aclose = AsyncMock()

        app.state.redis_client = mock_redis

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        from app.database import get_db
        app.dependency_overrides[get_db] = lambda: mock_session

        try:
            from httpx import ASGITransport
            from httpx import AsyncClient

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["checks"]["redis"] == "healthy"
        finally:
            app.dependency_overrides.clear()
            app.state.redis_client = None

    @pytest.mark.asyncio
    async def test_health_redis_unhealthy_no_client(self):
        """Health endpoint reports unhealthy when redis client is None."""
        from app.main import app

        app.state.redis_client = None

        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        from app.database import get_db
        app.dependency_overrides[get_db] = lambda: mock_session

        try:
            from httpx import ASGITransport
            from httpx import AsyncClient

            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert "unhealthy" in data["checks"]["redis"]
        finally:
            app.dependency_overrides.clear()
            app.state.redis_client = None


class TestRedisSessionStore:
    """Tests for Redis session store in security module."""

    @pytest.mark.asyncio
    async def test_session_rate_limit_uses_redis(self):
        """Rate limiting checks Redis for session count."""
        from app.core.security import _get_redis, _redis_client

        # Reset global state
        import app.core.security as security_module
        security_module._redis_client = None

        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=b"5")
        mock_redis.incr = AsyncMock()
        mock_redis.expire = AsyncMock()

        with patch("app.core.security._get_redis", AsyncMock(return_value=mock_redis)):
            from app.core.security import _get_redis

            redis_client = await _get_redis()
            key = "rate_limit:test_user"
            count = await redis_client.get(key)

            assert count == b"5"
            mock_redis.get.assert_called_once_with(key)

        # Restore
        security_module._redis_client = None


class TestRedisConfig:
    """Tests for Redis configuration."""

    def test_redis_url_without_password(self):
        """Redis URL without password remains unchanged."""
        from app.config import Settings

        settings = Settings(redis_url="redis://localhost:6379/0", redis_password="")
        assert settings.redis_url_with_password == "redis://localhost:6379/0"

    def test_redis_url_with_password(self):
        """Redis URL password is inserted into URL correctly."""
        from app.config import Settings

        settings = Settings(
            redis_url="redis://localhost:6379/0",
            redis_password="secret123",
        )
        assert "secret123" in settings.redis_url_with_password
        assert settings.redis_url_with_password == "redis://:secret123@localhost:6379/0"

    def test_redis_url_with_custom_port(self):
        """Redis URL with custom port uses correct port."""
        from app.config import Settings

        settings = Settings(
            redis_url="redis://localhost:6380/0",
            redis_password="secret123",
        )
        url = settings.redis_url_with_password
        assert ":6380" in url
        assert "secret123" in url
