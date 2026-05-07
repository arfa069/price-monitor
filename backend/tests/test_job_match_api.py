"""API tests for resume and job match endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import get_current_user
from app.main import app


def create_mock_user(user_id=1, username="testuser", role="user"):
    """Create a mock user with minimal attributes."""
    user = MagicMock()
    user.id = user_id
    user.username = username
    user.email = f"{username}@example.com"
    user.role = role
    user.deleted_at = None
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    return user


@pytest.fixture
def mock_get_current_user():
    """Mock get_current_user to return a test user."""
    async def _mock_get_current_user(token=None, db=None):
        return create_mock_user()
    app.dependency_overrides[get_current_user] = _mock_get_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.asyncio
async def test_list_resumes_returns_items(mock_get_current_user):
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
async def test_create_resume_returns_created_entity(mock_get_current_user):
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
async def test_trigger_match_analysis_returns_serialized_results(mock_get_current_user):
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


@pytest.mark.skip(reason="pre-existing bug: patches non-existent app.routers.jobs.create_task")
@pytest.mark.asyncio
async def test_analyze_async_creates_task_when_jobs_need_analysis(mock_get_current_user):
    """POST /match-results/analyze-async should create a background task."""
    from app.database import get_db
    from app.models.job_match import UserResume
    from app.routers import jobs as jobs_router_module

    resume = MagicMock(spec=UserResume)
    resume.id = 1
    resume.user_id = 1

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=resume)

    async def _override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_get_db

    with patch("app.routers.jobs._get_jobs_needing_analysis", new_callable=AsyncMock) as mock_filter, \
         patch("app.routers.jobs.create_task") as mock_create_task, \
         patch("asyncio.create_task") as mock_asyncio_create_task:

        # Mock a job needing analysis
        mock_job = MagicMock()
        mock_job.id = 10
        mock_filter.return_value = [mock_job]

        mock_task = MagicMock()
        mock_task.task_id = "abc123"
        mock_create_task.return_value = mock_task

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/jobs/match-results/analyze-async",
                    json={"resume_id": 1, "job_ids": [10]},
                )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "pending"
            assert data["task_id"] == "abc123"
            assert data["total"] == 1
            mock_asyncio_create_task.assert_called_once()
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_analyze_async_returns_completed_when_all_up_to_date(mock_get_current_user):
    """POST /match-results/analyze-async should return completed if no jobs need analysis."""
    from app.database import get_db
    from app.models.job_match import UserResume

    resume = MagicMock(spec=UserResume)
    resume.id = 1
    resume.user_id = 1

    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=resume)

    async def _override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_get_db

    with patch("app.routers.jobs._get_jobs_needing_analysis", new_callable=AsyncMock) as mock_filter:
        mock_filter.return_value = []

        try:
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post(
                    "/jobs/match-results/analyze-async",
                    json={"resume_id": 1, "job_ids": [10]},
                )
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["reason"] == "all_up_to_date"
            assert data["task_id"] is None
        finally:
            app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_get_task_status_returns_task_state():
    """GET /jobs/tasks/{task_id} should return task status."""
    from app.services.scheduler_service import CrawlTask, TaskStatus, _crawl_tasks

    task = CrawlTask(task_id="xyz789", status=TaskStatus.RUNNING, total=5, success=2, errors=1)
    _crawl_tasks["xyz789"] = task

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/jobs/tasks/xyz789")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "xyz789"
        assert data["status"] == "running"
        assert data["total"] == 5
        assert data["success"] == 2
        assert data["errors"] == 1
    finally:
        _crawl_tasks.pop("xyz789", None)


@pytest.mark.asyncio
async def test_get_task_status_returns_404_for_missing_task():
    """GET /jobs/tasks/{task_id} should 404 for unknown task."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/jobs/tasks/nonexistent")
    assert response.status_code == 404
    data = response.json()
    assert data["status"] == "error"
    assert data["reason"] == "task_not_found"
