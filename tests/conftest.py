"""Pytest configuration and fixtures for price monitor tests."""
from unittest.mock import MagicMock, patch
import pytest


# Pre-create mock task with proper id
mock_task = MagicMock()
mock_task.id = "test-task-id-12345"


# Smoke test marker — fast, no external dependencies
pytest_plugins = []


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session", autouse=True)
def patch_celery_send_task():
    with patch("app.routers.crawl.celery_app") as mock_celery:
        mock_celery.send_task.return_value = mock_task
        yield
