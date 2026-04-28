"""Module-level APScheduler job triggers (avoids circular imports)."""

import asyncio
import logging

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
