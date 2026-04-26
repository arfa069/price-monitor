"""Tests for the Boss Zhipin jobs API."""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_list_jobs_returns_paginated_response():
    """GET /jobs returns items with pagination metadata."""
    from app.database import get_db
    from app.models.job import Job

    mock_job = MagicMock(spec=Job)
    mock_job.id = 11
    mock_job.job_id = "test-job-id"
    mock_job.search_config_id = 7
    mock_job.title = "Python Engineer"
    mock_job.company = "Acme"
    mock_job.company_id = "company-1"
    mock_job.salary = "20-30K"
    mock_job.salary_min = 20
    mock_job.salary_max = 30
    mock_job.location = "Beijing"
    mock_job.experience = "3-5 years"
    mock_job.education = "Bachelor"
    mock_job.description = "Build things"
    mock_job.url = "https://example.com/jobs/11"
    mock_job.first_seen_at = datetime.now(UTC)
    mock_job.last_updated_at = datetime.now(UTC)
    mock_job.is_active = True

    mock_count = MagicMock()
    mock_count.scalar.return_value = 1

    mock_items = MagicMock()
    mock_items.scalars.return_value.all.return_value = [mock_job]

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(side_effect=[mock_count, mock_items])

    async def _override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/jobs?page=2&page_size=10")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["page"] == 2
        assert data["page_size"] == 10
        assert len(data["items"]) == 1
        assert data["items"][0]["job_id"] == "test-job-id"
    finally:
        app.dependency_overrides.clear()
