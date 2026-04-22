"""Pytest configuration and fixtures for price monitor tests."""
import pytest


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
