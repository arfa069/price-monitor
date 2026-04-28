"""Config API router."""
import logging

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.schemas.user import (
    JobCrawlCronUpdate,
    UserConfigCreate,
    UserConfigDefaults,
    UserConfigResponse,
    UserConfigUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["config"])

_DEFAULT_CONFIG = UserConfigDefaults()


def _get_scheduler():
    """Get scheduler from app state. Deferred import to avoid circular dependency."""
    # Deferred import: app is set by main.py lifespan after all modules are loaded
    import app.main
    return getattr(app.main.app.state, "scheduler", None)


def _remove_cron_job() -> None:
    """Remove the cron job if it exists. Called when cron mode is disabled."""
    scheduler = _get_scheduler()
    if scheduler is None:
        return
    job_id = "crawl_cron_job"
    try:
        existing = scheduler.get_job(job_id)
        if existing:
            scheduler.remove_job(job_id)
            logger.info("Removed cron job: %s", job_id)
    except Exception:
        logger.exception("Failed to remove cron job")


def _rebuild_scheduler_job(cron_expr: str, timezone_str: str) -> None:
    """Hot-reload the scheduler job when cron config changes.

    Removes existing job (if any) and adds a new one with the updated schedule.
    Gracefully handles the case where APScheduler is not yet initialized.
    """
    from app.services.scheduler_job import trigger_job_crawl

    scheduler = _get_scheduler()
    if scheduler is None:
        logger.info("Scheduler not initialized, skipping job rebuild")
        return

    job_id = "crawl_cron_job"
    try:
        existing = scheduler.get_job(job_id)
        if existing:
            scheduler.remove_job(job_id)
            logger.info("Removed existing cron job: %s", job_id)

        import zoneinfo

        from apscheduler.triggers.cron import CronTrigger
        tz = zoneinfo.ZoneInfo(timezone_str)
        scheduler.add_job(
            trigger_job_crawl,
            trigger=CronTrigger.from_crontab(cron_expr, timezone=tz),
            id=job_id,
            name="Crawl all active products",
            replace_existing=True,
            max_instances=1,
        )
        logger.info(
            "Registered cron job %s with schedule '%s' (tz=%s)",
            job_id, cron_expr, timezone_str,
        )
    except Exception:
        logger.exception("Failed to rebuild scheduler job")
        raise


def _rebuild_job_crawl_scheduler_job(cron_expr: str, timezone_str: str) -> None:
    """Hot-reload the job_crawl_cron APScheduler job. Used by PATCH /config and PUT /job-crawl-cron."""
    from app.services.scheduler_job import trigger_job_crawl

    scheduler = _get_scheduler()
    if scheduler is None:
        logger.info("Scheduler not initialized, skipping job_crawl job rebuild")
        return
    job_id = "job_crawl_cron_job"
    try:
        existing = scheduler.get_job(job_id)
        if existing:
            scheduler.remove_job(job_id)
            logger.info("Removed existing job_crawl_cron job")
        if cron_expr:
            import zoneinfo
            from apscheduler.triggers.cron import CronTrigger
            tz = zoneinfo.ZoneInfo(timezone_str)
            scheduler.add_job(
                trigger_job_crawl,
                trigger=CronTrigger.from_crontab(cron_expr, timezone=tz),
                id=job_id,
                name="Crawl all active job searches",
                replace_existing=True,
                max_instances=1,
            )
            logger.info("Registered job_crawl_cron_job with schedule '%s' (tz=%s)", cron_expr, timezone_str)
    except Exception:
        logger.exception("Failed to rebuild job_crawl_cron job")
        raise


async def _trigger_crawl_all() -> None:
    """APScheduler job callback: crawl all active products with concurrency protection."""
    from app.services.crawl import get_user_config, save_crawl_log
    from app.services.notification import send_feishu_notification
    from app.services.scheduler_service import crawl_all_products

    result = await crawl_all_products(source="cron")

    # Write summary log
    if result["status"] == "completed":
        await save_crawl_log(
            product_id=None,
            platform="system",
            status="CRON_SUCCESS",
            error_message=f"Completed: {result['total']} products",
        )
    elif result["status"] == "skipped":
        await save_crawl_log(
            product_id=None,
            platform="system",
            status="SKIPPED",
            error_message=result["reason"],
        )
    elif result["status"] == "error":
        await save_crawl_log(
            product_id=None,
            platform="system",
            status="CRON_ERROR",
            error_message=result.get("reason", "internal_error"),
        )
        # Send Feishu notification on failure
        try:
            user = await get_user_config()
            if user and user.feishu_webhook_url:
                await send_feishu_notification(
                    user.feishu_webhook_url,
                    "价格监控 Cron 调度执行失败，请检查日志。",
                )
        except Exception:
            logger.exception("Failed to send Feishu notification for cron failure")


@router.post("", response_model=UserConfigResponse)
async def create_or_update_config(
    config_data: UserConfigCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create or update user configuration."""
    result = await db.execute(select(User).where(User.id == 1))
    user = result.scalar_one_or_none()

    old_cron = user.crawl_cron if user else None

    if user is None:
        user = User(
            id=1,
            username="default",
            feishu_webhook_url=config_data.feishu_webhook_url,
            crawl_frequency_hours=config_data.crawl_frequency_hours,
            data_retention_days=config_data.data_retention_days,
            crawl_cron=config_data.crawl_cron,
            crawl_timezone=config_data.crawl_timezone or _DEFAULT_CONFIG.crawl_timezone,
        )
        db.add(user)
    else:
        user.feishu_webhook_url = config_data.feishu_webhook_url
        user.crawl_frequency_hours = config_data.crawl_frequency_hours
        user.data_retention_days = config_data.data_retention_days
        user.crawl_cron = config_data.crawl_cron
        user.crawl_timezone = config_data.crawl_timezone or _DEFAULT_CONFIG.crawl_timezone

    await db.commit()
    await db.refresh(user)

    # If cron config changed, rebuild or remove scheduler job
    if config_data.crawl_cron is not None and config_data.crawl_cron != old_cron:
        _rebuild_scheduler_job(
            config_data.crawl_cron,
            config_data.crawl_timezone or _DEFAULT_CONFIG.crawl_timezone,
        )
    elif config_data.crawl_cron is None and old_cron is not None:
        _remove_cron_job()

    return user


@router.get("", response_model=UserConfigResponse)
async def get_config(db: AsyncSession = Depends(get_db)):
    """Get current user configuration, or return defaults if not set."""
    result = await db.execute(select(User).where(User.id == 1))
    user = result.scalar_one_or_none()

    if user is None:
        return UserConfigResponse(
            id=0,
            username="default",
            feishu_webhook_url="",
            crawl_frequency_hours=_DEFAULT_CONFIG.crawl_frequency_hours,
            data_retention_days=_DEFAULT_CONFIG.data_retention_days,
            crawl_cron=_DEFAULT_CONFIG.crawl_cron,
            crawl_timezone=_DEFAULT_CONFIG.crawl_timezone,
            job_crawl_cron=_DEFAULT_CONFIG.job_crawl_cron,
        )

    return user


@router.get("/job-crawl-cron")
async def get_job_crawl_cron(db: AsyncSession = Depends(get_db)):
    """Get current job crawl cron expression."""
    result = await db.execute(select(User).where(User.id == 1))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "job_crawl_cron": user.job_crawl_cron,
        "default": "0 9 * * *",
        "timezone": user.crawl_timezone or "Asia/Shanghai",
    }


@router.put("/job-crawl-cron", response_model=JobCrawlCronUpdate)
async def update_job_crawl_cron(
    data: JobCrawlCronUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update job crawl cron expression and reschedule the APScheduler job."""
    result = await db.execute(select(User).where(User.id == 1))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    cron_expr = data.job_crawl_cron or ""
    if cron_expr.strip():
        from apscheduler.triggers.cron import CronTrigger
        try:
            import zoneinfo
            tz = zoneinfo.ZoneInfo(user.crawl_timezone or "Asia/Shanghai")
            CronTrigger.from_crontab(cron_expr, timezone=tz)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid cron expression")

    user.job_crawl_cron = cron_expr.strip() or None
    await db.commit()

    # Reschedule
    _rebuild_job_crawl_scheduler_job(
        user.job_crawl_cron or "0 9 * * *",
        user.crawl_timezone or "Asia/Shanghai",
    )

    return JobCrawlCronUpdate(job_crawl_cron=user.job_crawl_cron)


@router.patch("", response_model=UserConfigResponse)
async def update_config_partial(
    config_data: UserConfigUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Partial update user configuration (create if not exists)."""
    result = await db.execute(select(User).where(User.id == 1))
    user = result.scalar_one_or_none()

    old_cron = user.crawl_cron if user else None

    if user is None:
        user = User(
            id=1,
            username="default",
            feishu_webhook_url="",
            crawl_frequency_hours=_DEFAULT_CONFIG.crawl_frequency_hours,
            data_retention_days=_DEFAULT_CONFIG.data_retention_days,
            crawl_cron=config_data.crawl_cron,
            crawl_timezone=config_data.crawl_timezone or _DEFAULT_CONFIG.crawl_timezone,
        )
        db.add(user)
    else:
        update_data = config_data.model_dump(exclude_unset=True)
        if update_data:
            for field, value in update_data.items():
                setattr(user, field, value)

    await db.commit()
    await db.refresh(user)

    # If cron config changed, rebuild or remove scheduler job
    # Use model_fields_set to check if crawl_cron was explicitly provided
    model_fields_set = config_data.model_fields_set
    if "crawl_cron" in model_fields_set:
        if config_data.crawl_cron is not None and config_data.crawl_cron != old_cron:
            _rebuild_scheduler_job(
                config_data.crawl_cron,
                user.crawl_timezone or _DEFAULT_CONFIG.crawl_timezone,
            )
        elif config_data.crawl_cron is None and old_cron is not None:
            _remove_cron_job()

    return user
