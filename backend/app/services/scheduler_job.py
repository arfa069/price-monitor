"""Module-level APScheduler job triggers (avoids circular imports)."""

import asyncio
import logging
import zoneinfo

from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


async def trigger_job_crawl() -> None:
    """APScheduler job callback: crawl all active job searches.

    Defined at module level so main.py and config.py can both import it
    without circular dependencies. APScheduler holds a reference to this
    function — it must be importable by name, not a local function.
    """
    from app.services.job_crawl import crawl_all_job_searches
    logger.info("Job crawl cron triggered")
    asyncio.create_task(crawl_all_job_searches(source="cron"))


class JobConfigScheduler:
    """Manages per-config APScheduler jobs for job search crawl scheduling.

    Each JobSearchConfig can have its own cron expression. This manager
    encapsulates the add/remove/sync lifecycle, using job IDs in the
    format ``job_config_cron_{config_id}``.
    """

    JOB_ID_PREFIX = "job_config_cron_"

    def __init__(self, scheduler) -> None:
        self._scheduler = scheduler

    # ── Public API ──────────────────────────────────────────────

    def add_job(
        self,
        config_id: int,
        cron_expression: str,
        timezone: str = "Asia/Shanghai",
    ) -> None:
        """Register or replace a cron job for the given config."""
        if not cron_expression or not cron_expression.strip():
            self.remove_job(config_id)
            return

        job_id = self._job_id(config_id)
        tz = zoneinfo.ZoneInfo(timezone)

        from app.services.job_crawl import crawl_single_config

        self._scheduler.add_job(
            crawl_single_config,
            trigger=CronTrigger.from_crontab(cron_expression, timezone=tz),
            id=job_id,
            name=f"JobConfig crawl #{config_id}",
            replace_existing=True,
            max_instances=1,
            kwargs={"config_id": config_id},
        )
        logger.info(
            "Registered cron job %s with schedule '%s' (tz=%s)",
            job_id, cron_expression, timezone,
        )

    def remove_job(self, config_id: int) -> None:
        """Remove the cron job for a config (if it exists)."""
        job_id = self._job_id(config_id)
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
            logger.info("Removed cron job %s", job_id)

    async def sync_all(self) -> None:
        """Sync scheduler state with the database on startup."""
        from sqlalchemy import select
        from app.database import AsyncSessionLocal
        from app.models.job import JobSearchConfig

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(JobSearchConfig).where(
                    JobSearchConfig.cron_expression.isnot(None),
                    JobSearchConfig.user_id == 1,
                )
            )
            configs = result.scalars().all()

        for config in configs:
            self.add_job(
                config_id=config.id,
                cron_expression=config.cron_expression,
                timezone=config.cron_timezone or "Asia/Shanghai",
            )

        logger.info("JobConfigScheduler synced: %d config jobs registered", len(configs))

    def get_next_run_times(self) -> dict[int, dict]:
        """Return next run time info for all registered config jobs."""
        result: dict[int, dict] = {}
        for job in self._scheduler.get_jobs():
            if not job.id.startswith(self.JOB_ID_PREFIX):
                continue
            config_id = int(job.id[len(self.JOB_ID_PREFIX):])
            result[config_id] = {
                "cron_expression": str(job.trigger),
                "next_run_at": job.next_run_time.isoformat() if job.next_run_time else None,
            }
        return result

    # ── Internal helpers ────────────────────────────────────────────

    def _job_id(self, config_id: int) -> str:
        return f"{self.JOB_ID_PREFIX}{config_id}"
