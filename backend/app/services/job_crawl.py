"""Job crawling service: process results, deduplicate, send notifications."""
from __future__ import annotations

import asyncio
import logging
import random
import re
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.platforms import BossZhipinAdapter

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.job import Job, JobSearchConfig
from app.models.job_crawl_log import JobCrawlLog
from app.models.job_match import UserResume
from app.services.job_match import analyze_resume_vs_jobs
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

        # Batch query: find all jobs by job_id in ONE query
        job_ids = [job["job_id"] for job in jobs if job.get("job_id")]
        job_id_to_data: dict[str, dict] = {job["job_id"]: job for job in jobs if job.get("job_id")}

        jobs_by_job_id: dict[str, Job] = {}
        if job_ids:
            result = await db.execute(
                select(Job).where(Job.job_id.in_(job_ids))
            )
            for job in result.scalars().all():
                jobs_by_job_id[job.job_id] = job

        # Separate into found by job_id vs need dedup check
        jobs_need_dedup: list[dict] = []  # jobs not found by job_id, need dedup by (title, company, salary)

        for job_id, job_obj in jobs_by_job_id.items():
            if job_id not in job_id_to_data:
                continue  # Skip jobs not in our input data (mock may return unexpected results)
            job_data = job_id_to_data[job_id]
            salary = job_data.get("salary")
            salary_min, salary_max = parse_salary(salary)
            # Update existing job
            job_obj.last_updated_at = datetime.now(UTC)
            job_obj.is_active = True
            if job_data.get("title"):
                job_obj.title = job_data["title"]
            if job_data.get("company"):
                job_obj.company = job_data["company"]
            if salary:
                job_obj.salary = salary
                job_obj.salary_min = salary_min
                job_obj.salary_max = salary_max
            if job_data.get("location"):
                job_obj.location = job_data["location"]
            if job_data.get("experience"):
                job_obj.experience = job_data["experience"]
            if job_data.get("education"):
                job_obj.education = job_data["education"]
            if job_data.get("url"):
                job_obj.url = job_data["url"]
            updated_count += 1

        for job_data in jobs:
            job_id = job_data.get("job_id")
            if not job_id or job_id in jobs_by_job_id:
                continue
            # Not found by job_id — collect for dedup check
            salary = job_data.get("salary")
            salary_min, salary_max = parse_salary(salary)
            jobs_need_dedup.append({
                "job_id": job_id,
                "data": job_data,
                "salary": salary,
                "salary_min": salary_min,
                "salary_max": salary_max,
                "title": job_data.get("title") or "",
                "company": job_data.get("company") or "",
                "company_id": job_data.get("company_id") or "",
                "location": job_data.get("location") or "",
                "experience": job_data.get("experience") or "",
                "education": job_data.get("education") or "",
                "url": job_data.get("url") or "",
            })

        # Batch dedup query: find all matching by (title, company, salary) in ONE query
        newly_inserted_job_ids: list[str] = []  # track string job_ids of new inserts
        if jobs_need_dedup:
            dedup_tuples = [(j["title"], j["company"], j["salary"] or "") for j in jobs_need_dedup]
            result = await db.execute(
                select(Job).where(
                    Job.search_config_id == config_id,
                    Job.title.in_([t[0] for t in dedup_tuples]),
                    Job.company.in_([t[1] for t in dedup_tuples]),
                    Job.salary.in_([t[2] for t in dedup_tuples]),
                )
            )
            # Build dedup lookup: (title, company, salary) -> Job
            dedup_map: dict[tuple[str, str, str], Job] = {}
            for job in result.scalars().all():
                dedup_map[(job.title, job.company, job.salary or "")] = job

            now = datetime.now(UTC)
            for item in jobs_need_dedup:
                key = (item["title"], item["company"], item["salary"])
                existing_dup = dedup_map.get(key)
                if existing_dup:
                    # Update existing record with new job_id
                    existing_dup.job_id = item["job_id"]
                    existing_dup.last_updated_at = now
                    existing_dup.is_active = True
                    if item["location"]:
                        existing_dup.location = item["location"]
                    if item["experience"]:
                        existing_dup.experience = item["experience"]
                    if item["education"]:
                        existing_dup.education = item["education"]
                    if item["url"]:
                        existing_dup.url = item["url"]
                    updated_count += 1
                else:
                    # Insert new job
                    newly_inserted_job_ids.append(item["job_id"])
                    new_job = Job(
                        job_id=item["job_id"],
                        search_config_id=config_id,
                        title=item["title"],
                        company=item["company"],
                        company_id=item["company_id"],
                        salary=item["salary"],
                        salary_min=item["salary_min"],
                        salary_max=item["salary_max"],
                        location=item["location"],
                        experience=item["experience"],
                        education=item["education"],
                        url=item["url"],
                        first_seen_at=now,
                        last_updated_at=now,
                        is_active=True,
                    )
                    db.add(new_job)
                    new_count += 1

        # Flush all new jobs and fetch their internal IDs
        if newly_inserted_job_ids:
            await db.flush()
            result = await db.execute(
                select(Job.id).where(Job.job_id.in_(newly_inserted_job_ids))
            )
            new_job_ids = [row[0] for row in result.all()]

        # Send notification for new jobs (after commit so config.notify_on_new is available)
        if new_count > 0 and config.notify_on_new:
            try:
                await send_new_job_notification(config, new_count, total_scraped)
            except Exception:
                logger.exception("Failed to send job notification for config %s", config_id)

        # Log crawl result — in same transaction as job inserts/updates
        crawl_log = JobCrawlLog(
            search_config_id=config.id,
            status="SUCCESS",
            new_jobs_count=new_count,
            total_jobs_count=total_scraped,
            scraped_at=datetime.now(UTC),
            error_message=None,
        )
        db.add(crawl_log)

        # Single commit for both job data and crawl log
        await db.commit()

        # Fetch job details sequentially with rate limiting (no concurrency)
        if new_job_ids:
            detail_errors = 0
            consecutive_cookie_failures = 0
            for jid in new_job_ids:
                try:
                    result = await update_job_detail(jid, adapter=adapter)
                    if isinstance(result, Exception):
                        detail_errors += 1
                    elif isinstance(result, dict) and not result.get("success"):
                        detail_errors += 1
                        err = result.get("error", "")
                        if "code=37" in err or "code=36" in err or "Cookie expired" in err:
                            consecutive_cookie_failures += 1
                        else:
                            consecutive_cookie_failures = 0
                    else:
                        consecutive_cookie_failures = 0
                except Exception:
                    detail_errors += 1
                    consecutive_cookie_failures += 1

                # 连续 3 次 cookie 失败 → token 彻底失效，停止获取详情
                if consecutive_cookie_failures >= 3:
                    remaining = len(new_job_ids) - new_job_ids.index(jid) - 1
                    logger.warning(
                        "Bailing out of detail fetch: %d consecutive cookie failures, "
                        "%d jobs remaining",
                        consecutive_cookie_failures, remaining,
                    )
                    break

                # 2-5秒间隔，避免触发反爬
                await asyncio.sleep(random.uniform(2.0, 5.0))
            if detail_errors:
                logger.info("Detail fetch completed: %d errors out of %d jobs", detail_errors, len(new_job_ids))

        if new_job_ids and config.enable_match_analysis:
            resume_result = await db.execute(
                select(UserResume).where(UserResume.user_id == config.user_id)
            )
            resumes = list(resume_result.scalars().all())
            for resume in resumes:
                try:
                    await analyze_resume_vs_jobs(resume.id, new_job_ids)
                except Exception:
                    logger.exception("Failed to run match analysis for resume %s", resume.id)

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
            log = JobCrawlLog(
                search_config_id=config_id,
                status="ERROR",
                error_message=result.get("error", "Unknown error"),
                scraped_at=datetime.now(UTC),
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


async def crawl_single_config_background(config_id: int) -> "CrawlTask":
    """后台运行单配置爬取，立即返回 task 对象。"""
    from app.services.scheduler_service import CrawlTask, TaskStatus, create_task

    task = create_task("manual")
    task.status = TaskStatus.RUNNING

    async def _run():
        try:
            result = await crawl_single_config(config_id)
            ok = result.get("status") != "error"
            task.status = TaskStatus.COMPLETED if ok else TaskStatus.FAILED
            task.total = sum(v for k, v in result.items() if k in ("new_count", "updated_count", "deactivated_count"))
            task.success = result.get("new_count", 0)
            task.errors = 0 if ok else 1
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.reason = str(e)

    asyncio.create_task(_run())
    return task


async def crawl_all_job_searches_background() -> "CrawlTask":
    """后台运行全量爬取，立即返回 task 对象。"""
    from app.services.scheduler_service import CrawlTask, TaskStatus, create_task

    task = create_task("manual")
    task.status = TaskStatus.RUNNING

    async def _run():
        try:
            result = await crawl_all_job_searches(source="manual")
            ok = result.get("status") != "error"
            task.status = TaskStatus.COMPLETED if ok else TaskStatus.FAILED
            task.total = result.get("total", 0)
            task.success = result.get("success", 0)
            task.errors = result.get("errors", 0)
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.reason = str(e)

    asyncio.create_task(_run())
    return task
