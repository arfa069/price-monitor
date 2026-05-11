"""Pytest configuration and fixtures for price monitor tests."""
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def _isolate_module_level_redis_singletons():
    """Isolate module-level _redis_client singletons across tests.

    Why: `app.core.security` and `app.services.user_config_cache` cache the
    redis client in a module-global. pytest-asyncio uses a fresh event loop
    per test, but the cached client stays bound to the loop where it was
    first created — subsequent tests then hit "Event loop is closed" when
    awaiting that client. Replacing the singleton with an AsyncMock before
    each test (and clearing it after) avoids the leak without touching
    production code, where the single-loop assumption is fine.
    """
    from app.core import security as _security
    from app.services import user_config_cache as _ucc

    fake = AsyncMock()
    fake.get = AsyncMock(return_value=None)
    fake.incr = AsyncMock(return_value=1)
    fake.expire = AsyncMock(return_value=True)
    fake.delete = AsyncMock(return_value=1)
    fake.ttl = AsyncMock(return_value=900)
    fake.setex = AsyncMock(return_value=True)
    fake.set = AsyncMock(return_value=True)
    fake.ping = AsyncMock(return_value=True)

    _security._redis_client = fake
    _ucc._redis_client = fake
    try:
        yield fake
    finally:
        _security._redis_client = None
        _ucc._redis_client = None


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client for integration tests."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def test_user() -> dict:
    """Test user data for authentication tests."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "securepassword123",
    }


@pytest.fixture
def another_user() -> dict:
    """Another test user for conflict tests."""
    return {
        "username": "anotheruser",
        "email": "another@example.com",
        "password": "anotherpassword456",
    }

