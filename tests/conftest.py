"""Pytest configuration and fixtures for price monitor tests."""
import pytest


# Smoke test marker — fast, no external dependencies
pytest_plugins = []


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"
