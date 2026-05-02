"""JobConfigScheduler: per-config cron management for job search crawl."""

import logging
import zoneinfo

from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)


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


class ProductCronScheduler:
    """Manages per-platform APScheduler jobs for product crawl scheduling.

    Each platform (taobao, jd, amazon) can have its own cron expression.
    Job IDs follow the format ``product_cron_{platform}``.
    """

    JOB_ID_PREFIX = "product_cron_"

    def __init__(self, scheduler) -> None:
        self._scheduler = scheduler

    # ── Public API ──────────────────────────────────────────────

    def add_job(
        self,
        platform: str,
        cron_expression: str,
        timezone: str = "Asia/Shanghai",
    ) -> None:
        """Register or replace a cron job for the given platform."""
        if not cron_expression or not cron_expression.strip():
            self.remove_job(platform)
            return

        job_id = self._job_id(platform)
        tz = zoneinfo.ZoneInfo(timezone)

        from app.services.scheduler_service import crawl_products_by_platform

        self._scheduler.add_job(
            crawl_products_by_platform,
            trigger=CronTrigger.from_crontab(cron_expression, timezone=tz),
            id=job_id,
            name=f"Product crawl {platform}",
            replace_existing=True,
            max_instances=1,
            kwargs={"platform": platform},
        )
        logger.info(
            "Registered cron job %s with schedule '%s' (tz=%s)",
            job_id, cron_expression, timezone,
        )

    def remove_job(self, platform: str) -> None:
        """Remove the cron job for a platform (if it exists)."""
        job_id = self._job_id(platform)
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)
            logger.info("Removed cron job %s", job_id)

    async def sync_all(self) -> None:
        """Ensure 3 platform rows exist and register cron jobs."""
        from sqlalchemy import select
        from app.database import AsyncSessionLocal
        from app.models.product import ProductPlatformCron

        async with AsyncSessionLocal() as db:
            # Ensure rows exist for all 3 platforms
            for plat in ("taobao", "jd", "amazon"):
                result = await db.execute(
                    select(ProductPlatformCron).where(
                        ProductPlatformCron.platform == plat,
                        ProductPlatformCron.user_id == 1,
                    )
                )
                config = result.scalar_one_or_none()
                if not config:
                    db.add(ProductPlatformCron(
                        user_id=1, platform=plat,
                        cron_expression=None, cron_timezone="Asia/Shanghai",
                    ))
            await db.commit()

            # Read all and register
            result = await db.execute(
                select(ProductPlatformCron).where(
                    ProductPlatformCron.cron_expression.isnot(None),
                    ProductPlatformCron.user_id == 1,
                )
            )
            configs = result.scalars().all()

        for config in configs:
            self.add_job(
                platform=config.platform,
                cron_expression=config.cron_expression,
                timezone=config.cron_timezone or "Asia/Shanghai",
            )

        logger.info("ProductCronScheduler synced: %d platform jobs registered", len(configs))

    def get_next_run_times(self) -> dict[str, dict]:
        """Return next run time info for all registered platform jobs."""
        result: dict[str, dict] = {}
        for job in self._scheduler.get_jobs():
            if not job.id.startswith(self.JOB_ID_PREFIX):
                continue
            platform = job.id[len(self.JOB_ID_PREFIX):]
            result[platform] = {
                "cron_expression": str(job.trigger),
                "next_run_at": job.next_run_time.isoformat() if job.next_run_time else None,
            }
        return result

    def _job_id(self, platform: str) -> str:
        return f"{self.JOB_ID_PREFIX}{platform}"
