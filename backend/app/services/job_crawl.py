"""Job crawling service: process results, deduplicate, send notifications."""
from __future__ import annotations

import asyncio
import logging
import random
import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.platforms import BossZhipinAdapter

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.crawl_log import CrawlLog
from app.models.job import Job, JobSearchConfig
from app.services.notification import send_new_job_notification

logger = logging.getLogger(__name__)


def parse_salary(salary_str: str | None) -> tuple[int | None, int | None]:
    """Parse salary string like '20-40K·14薪' to (min, max) in K.

    Returns:
        (salary_min, salary_max) in units of K, or (None, None) if unparseable.
    """
    if not salary_str:
        return None, None

    # Remove bonus part like "·14薪"
    salary_str = re.sub(r'·\d+薪', '', salary_str)

    # Match patterns like "20-40K", "20K", "20-40k", "面议"
    if salary_str in ('面议', '薪资面议', '薪资面议 '):
        return None, None

    # Remove spaces and clean up
    salary_str = re.sub(r'\s+', '', salary_str)

    match = re.match(r'(\d+)[kK]?-(\d+)[kK]?', salary_str)
    if match:
        return int(match.group(1)), int(match.group(2))

    # Single value like "20K"
    match = re.match(r'^(\d+)[kK]?$', salary_str.strip())
    if match:
        val = int(match.group(1))
        return val, val

    return None, None


async def process_job_results(
    config_id: int,
    jobs: list[dict],
    total_scraped: int,
    adapter: BossZhipinAdapter | None = None,
) -> dict:
    """Process crawl results: deduplicate, insert/update jobs, send notifications.

    Args:
        config_id: The JobSearchConfig ID that was crawled
        jobs: List of job data dicts from BossZhipinAdapter
        total_scraped: Total number of jobs seen in this crawl (for logging)

    Returns:
        {"new_count": N, "updated_count": N, "deactivated_count": N}
    """
    new_count = 0
    updated_count = 0
    deactivated_count = 0
    new_job_ids: list[int] = []

    async with AsyncSessionLocal() as db:
        config = await db.get(JobSearchConfig, config_id)
        if not config:
            logger.warning(f"JobSearchConfig {config_id} not found")
            return {"new_count": 0, "updated_count": 0, "deactivated_count": 0}

        # Get job_ids seen in this crawl
        seen_job_ids = {job["job_id"] for job in jobs if job.get("job_id")}

        # Deactivate jobs that were seen last time but not this time (grace period)
        if seen_job_ids:
            result = await db.execute(
                select(Job).where(
                    Job.search_config_id == config_id,
                    Job.is_active,
                )
            )
            all_active_jobs = list(result.scalars().all())

            threshold = config.deactivation_threshold or 3

            for job in all_active_jobs:
                if job.job_id in seen_job_ids:
                    # Job is still present — reset counter
                    job.consecutive_miss_count = 0
                    job.last_active_at = datetime.now(UTC)
                else:
                    # Job not seen this crawl — increment miss counter
                    job.consecutive_miss_count = (job.consecutive_miss_count or 0) + 1
                    if job.consecutive_miss_count >= threshold:
                        job.is_active = False
                        job.last_updated_at = datetime.now(UTC)
                        deactivated_count += 1

        # Process each scraped job
        for job_data in jobs:
            job_id = job_data.get("job_id")
            if not job_id:
                continue

            result = await db.execute(
                select(Job).where(Job.job_id == job_id)
            )
            existing = result.scalar_one_or_none()

            salary = job_data.get("salary")
            salary_min, salary_max = parse_salary(salary)

            if existing:
                # Update existing job
                existing.last_updated_at = datetime.now(UTC)
                existing.is_active = True
                # Update fields if changed
                if job_data.get("title"):
                    existing.title = job_data["title"]
                if job_data.get("company"):
                    existing.company = job_data["company"]
                if salary:
                    existing.salary = salary
                    existing.salary_min = salary_min
                    existing.salary_max = salary_max
                if job_data.get("location"):
                    existing.location = job_data["location"]
                if job_data.get("experience"):
                    existing.experience = job_data["experience"]
                if job_data.get("education"):
                    existing.education = job_data["education"]
                if job_data.get("url"):
                    existing.url = job_data["url"]
                updated_count += 1
            else:
                # Insert new job
                new_job = Job(
                    job_id=job_id,
                    search_config_id=config_id,
                    title=job_data.get("title") or "",
                    company=job_data.get("company") or "",
                    company_id=job_data.get("company_id") or "",
                    salary=salary or "",
                    salary_min=salary_min,
                    salary_max=salary_max,
                    location=job_data.get("location") or "",
                    experience=job_data.get("experience") or "",
                    education=job_data.get("education") or "",
                    url=job_data.get("url") or "",
                    first_seen_at=datetime.now(UTC),
                    last_updated_at=datetime.now(UTC),
                    is_active=True,
                )
                db.add(new_job)
                await db.flush()  # Get the inserted job's id
                new_count += 1
                new_job_ids.append(new_job.id)

        # Send notification for new jobs (after commit so config.notify_on_new is available)
        if new_count > 0 and config.notify_on_new:
            try:
                await send_new_job_notification(config, new_count, total_scraped)
            except Exception:
                logger.exception("Failed to send job notification for config %s", config_id)

        # Log crawl result — in same transaction as job inserts/updates
        crawl_log = CrawlLog(
            product_id=None,  # job crawl, not a product
            platform="boss",
            status="SUCCESS",
            price=Decimal(new_count),
            currency=None,
            timestamp=datetime.now(UTC),
            error_message=None,
        )
        db.add(crawl_log)

        # Single commit for both job data and crawl log
        await db.commit()

        # Fetch job details sequentially with rate limiting (no concurrency)
        if new_job_ids:
            detail_errors = 0
            for jid in new_job_ids:
                try:
                    result = await update_job_detail(jid, adapter=adapter)
                    if isinstance(result, Exception):
                        detail_errors += 1
                except Exception:
                    detail_errors += 1
                # 2-5秒间隔，避免触发反爬
                await asyncio.sleep(random.uniform(2.0, 5.0))
            if detail_errors:
                logger.info("Detail fetch completed: %d errors out of %d jobs", detail_errors, len(new_job_ids))

    return {
        "new_count": new_count,
        "updated_count": updated_count,
        "deactivated_count": deactivated_count,
    }


async def update_job_detail(job_id: int, adapter: BossZhipinAdapter | None = None) -> dict:
    """Fetch and update job detail (description, address) from Boss API.

    Args:
        job_id: The internal Job record ID.
        adapter: Optional shared BossZhipinAdapter instance (reuses session/cookies).

    Returns:
        {"success": True, "detail": {...}} or {"success": False, "error": "..."}
    """
    from app.platforms import BossZhipinAdapter

    async with AsyncSessionLocal() as db:
        job = await db.get(Job, job_id)
        if not job:
            return {"success": False, "error": "Job not found"}

        # Reuse adapter if provided (shares session & cookies), else create new
        if adapter is None:
            adapter = BossZhipinAdapter()
        result = await adapter.crawl_detail(job.job_id)

        if not result.get("success"):
            return result

        detail = result["detail"]

        # Update job record with detail data
        job.description = detail.get("description", "")
        job.address = detail.get("address", "")
        job.last_updated_at = datetime.now(UTC)
        await db.commit()

        return {"success": True, "detail": detail}


async def crawl_single_config(
    config_id: int, adapter: "BossZhipinAdapter | None" = None
) -> dict:
    """Crawl a single JobSearchConfig and process results.

    Args:
        config_id: The JobSearchConfig ID to crawl.
        adapter: Optional shared BossZhipinAdapter. When provided, reuses
            the adapter's session and cookies across multiple configs to
            avoid redundant cookie acquisition and browser tab churn.
    """
    from app.platforms import BossZhipinAdapter

    async with AsyncSessionLocal() as db:
        config = await db.get(JobSearchConfig, config_id)
        if not config:
            return {"status": "error", "error": "Config not found"}

    if adapter is None:
        adapter = BossZhipinAdapter()
    result = await adapter.crawl(config.url)

    if result.get("success"):
        stats = await process_job_results(
            config_id=config_id,
            jobs=result["jobs"],
            total_scraped=result["count"],
            adapter=adapter,
        )
        return {"status": "success", **stats}
    else:
        # Log error
        async with AsyncSessionLocal() as db:
            log = CrawlLog(
                product_id=None,  # job crawl, not a product
                platform="boss",
                status="ERROR",
                price=None,
                currency=None,
                timestamp=datetime.now(UTC),
                error_message=result.get("error", "Unknown error"),
            )
            db.add(log)
            await db.commit()
        return {"status": "error", "error": result.get("error")}


async def crawl_all_job_searches(source: str = "manual") -> dict:
    """Crawl all active job search configs.

    Shares a single BossZhipinAdapter across all configs so that cookie
    acquisition (including any browser-tab refresh) happens at most once
    instead of once per config.
    """
    from app.platforms import BossZhipinAdapter

    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(JobSearchConfig).where(JobSearchConfig.active)
        )
        configs = list(result.scalars().all())

    if not configs:
        return {"status": "completed", "total": 0, "success": 0, "errors": 0}

    total = len(configs)
    success_count = 0
    error_count = 0
    details = []

    adapter = BossZhipinAdapter()

    for i, config in enumerate(configs):
        result = await crawl_single_config(config.id, adapter=adapter)
        details.append({"config_id": config.id, **result})
        if result.get("status") == "success":
            success_count += 1
        else:
            error_count += 1

        if i < len(configs) - 1:
            delay = random.uniform(3, 6)
            logger.debug("Waiting %.1fs before next config", delay)
            await asyncio.sleep(delay)

    return {
        "status": "completed",
        "total": total,
        "success": success_count,
        "errors": error_count,
        "details": details,
    }
