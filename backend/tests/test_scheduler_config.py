"""Tests for JobConfigScheduler manager."""
import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler


@pytest.fixture
async def scheduler():
    s = AsyncIOScheduler()
    s.start()
    yield s
    s.shutdown(wait=False)


@pytest.mark.asyncio
async def test_add_job(scheduler):
    """Should add an APScheduler job for a given config."""
    from app.services.scheduler_job import JobConfigScheduler

    mgr = JobConfigScheduler(scheduler)
    mgr.add_job(config_id=1, cron_expression="0 9 * * *", timezone="Asia/Shanghai")

    job = scheduler.get_job("job_config_cron_1")
    assert job is not None


@pytest.mark.asyncio
async def test_remove_job(scheduler):
    """Should remove the APScheduler job for a given config."""
    from app.services.scheduler_job import JobConfigScheduler

    mgr = JobConfigScheduler(scheduler)
    mgr.add_job(config_id=1, cron_expression="0 9 * * *", timezone="Asia/Shanghai")
    mgr.remove_job(config_id=1)

    job = scheduler.get_job("job_config_cron_1")
    assert job is None


@pytest.mark.asyncio
async def test_replace_job(scheduler):
    """Should replace existing job when add_job called again."""
    from app.services.scheduler_job import JobConfigScheduler

    mgr = JobConfigScheduler(scheduler)
    mgr.add_job(config_id=1, cron_expression="0 9 * * *", timezone="Asia/Shanghai")
    mgr.add_job(config_id=1, cron_expression="0 18 * * *", timezone="Asia/Shanghai")

    job = scheduler.get_job("job_config_cron_1")
    assert job is not None


@pytest.mark.asyncio
async def test_empty_cron_removes_job(scheduler):
    """Should remove job when add_job called with empty cron expression."""
    from app.services.scheduler_job import JobConfigScheduler

    mgr = JobConfigScheduler(scheduler)
    mgr.add_job(config_id=1, cron_expression="0 9 * * *", timezone="Asia/Shanghai")
    mgr.add_job(config_id=1, cron_expression="", timezone="Asia/Shanghai")

    job = scheduler.get_job("job_config_cron_1")
    assert job is None


@pytest.mark.asyncio
async def test_get_next_run_times(scheduler):
    """Should return next run times for all config jobs."""
    from app.services.scheduler_job import JobConfigScheduler

    mgr = JobConfigScheduler(scheduler)
    mgr.add_job(config_id=1, cron_expression="0 9 * * *", timezone="Asia/Shanghai")

    result = mgr.get_next_run_times()
    assert 1 in result
    assert "next_run_at" in result[1]
