"""API tests for resume and job match endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_list_resumes_returns_items():
    """GET /jobs/resumes returns uploaded resumes."""
    from app.database import get_db
    from app.models.job_match import UserResume

    resume = MagicMock(spec=UserResume)
    resume.id = 1
    resume.user_id = 1
    resume.name = "Resume A"
    resume.resume_text = "Python engineer"
    resume.created_at = datetime.now(UTC)
    resume.updated_at = datetime.now(UTC)

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [resume]

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=mock_result)

    async def _override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/jobs/resumes")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Resume A"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_create_resume_returns_created_entity():
    """POST /jobs/resumes creates a resume."""
    from datetime import UTC, datetime

    from app.database import get_db

    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock(
        side_effect=lambda resume: (
            setattr(resume, "id", 99),
            setattr(resume, "created_at", datetime.now(UTC)),
            setattr(resume, "updated_at", datetime.now(UTC)),
        )
    )

    async def _override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/jobs/resumes",
                json={"name": "Resume B", "resume_text": "Frontend engineer"},
            )
        assert response.status_code == 201
        data = response.json()
        assert data["id"] == 99
        assert data["name"] == "Resume B"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_trigger_match_analysis_returns_serialized_results():
    """POST /jobs/match-results/analyze returns match results payload."""
    from app.database import get_db
    from app.models.job import Job
    from app.models.job_match import MatchResult, UserResume
    from app.routers import jobs as jobs_router_module

    resume = MagicMock(spec=UserResume)
    resume.id = 1
    resume.user_id = 1

    job = MagicMock(spec=Job)
    job.title = "Python Engineer"
    job.company = "Acme"
    job.salary = "20-30K"
    job.location = "Shanghai"
    job.url = "https://example.com/jobs/1"
    job.description = "Build APIs"

    match = MagicMock(spec=MatchResult)
    match.id = 7
    match.user_id = 1
    match.resume_id = 1
    match.job_id = 10
    match.match_score = 88
    match.match_reason = "Strong Python background"
    match.apply_recommendation = "强烈推荐"
    match.llm_model_used = "gpt-4o-mini"
    match.created_at = datetime.now(UTC)
    match.updated_at = datetime.now(UTC)
    match.job = job

    mock_resume_result = MagicMock()
    mock_resume_result.scalar_one_or_none.return_value = resume

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=resume)

    async def _override_get_db():
        yield mock_session

    async def _fake_analyze_resume_vs_jobs(resume_id: int, job_ids: list[int] | None):
        assert resume_id == 1
        assert job_ids == [10]
        return {
            "processed": 1,
            "created": 1,
            "updated": 0,
            "skipped": 0,
            "items": [match],
        }

    app.dependency_overrides[get_db] = _override_get_db
    original = jobs_router_module.analyze_resume_vs_jobs
    try:
        jobs_router_module.analyze_resume_vs_jobs = _fake_analyze_resume_vs_jobs
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/jobs/match-results/analyze",
                json={"resume_id": 1, "job_ids": [10]},
            )
        assert response.status_code == 200
        data = response.json()
        assert data["processed"] == 1
        assert data["items"][0]["match_score"] == 88
        assert data["items"][0]["job_title"] == "Python Engineer"
    finally:
        jobs_router_module.analyze_resume_vs_jobs = original
        app.dependency_overrides.clear()
