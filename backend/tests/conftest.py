"""Pytest configuration and fixtures for price monitor tests."""
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


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

