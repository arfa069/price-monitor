"""FastAPI application entry point."""
import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi.responses import JSONResponse

# Windows requires ProactorEventLoop for subprocess support (Playwright spawns browser drivers)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.api.admin import admin_router
from app.api.admin import router as admin_users_router
from app.api.auth import router as auth_router
from app.api.wechat import router as wechat_router
from app.config import settings
from app.database import engine
from app.routers import alerts, config, crawl, products
from app.routers.jobs import router as jobs_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    app.state.redis_client = redis.from_url(settings.redis_url_with_password)
    await _start_scheduler(app)
    yield
    # Shutdown: stop scheduler gracefully
    await _stop_scheduler(app)
    # Close database engine connections
    await engine.dispose()
    # Close Redis connection
    await app.state.redis_client.aclose()


async def _start_scheduler(app: FastAPI) -> None:
    """Initialize APScheduler with AsyncIOScheduler and register cron job from DB config."""

    from apscheduler.schedulers.asyncio import AsyncIOScheduler

    # Initialize concurrency lock
    app.state.crawl_lock = asyncio.Semaphore(1)

    # Register state with scheduler service (shared by cron and manual crawl)
    from app.services.scheduler_service import _set_scheduler_state
    _set_scheduler_state({"crawl_lock": app.state.crawl_lock})

    scheduler = AsyncIOScheduler(timezone="UTC", job_defaults={"coalesce": True, "max_instances": 1})
    app.state.scheduler = scheduler

    # 职位爬取使用 per-config 独立 cron 调度
    from app.services.scheduler_job import JobConfigScheduler, ProductCronScheduler
    job_config_scheduler = JobConfigScheduler(scheduler)
    app.state.job_config_scheduler = job_config_scheduler
    await job_config_scheduler.sync_all()

    # 商品爬取使用 per-platform 独立 cron 调度
    product_cron_scheduler = ProductCronScheduler(scheduler)
    app.state.product_cron_scheduler = product_cron_scheduler
    await product_cron_scheduler.sync_all()

    scheduler.start()
    logger.info("APScheduler started")


async def _stop_scheduler(app: FastAPI) -> None:
    """Gracefully shutdown APScheduler."""
    scheduler = getattr(app.state, "scheduler", None)
    if scheduler and scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("APScheduler shutdown complete")


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

# CORS middleware - restrict origins in production
_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(config.router)
app.include_router(products.router)
app.include_router(alerts.router)
app.include_router(crawl.router)
app.include_router(jobs_router)
app.include_router(auth_router)
app.include_router(wechat_router)
app.include_router(admin_users_router)
app.include_router(admin_router)

# Scheduler status endpoint
@app.get("/scheduler/status", tags=["scheduler"])
async def get_scheduler_status():
    """Get APScheduler status and next run times for all cron jobs."""
    scheduler = getattr(app.state, "scheduler", None)

    if scheduler is None:
        return JSONResponse(
            status_code=503,
            content={"scheduler": "not_started"},
        )

    from app.services.scheduler_job import JobConfigScheduler, ProductCronScheduler
    job_config_scheduler: JobConfigScheduler = getattr(app.state, "job_config_scheduler", None)
    product_cron_scheduler: ProductCronScheduler = getattr(app.state, "product_cron_scheduler", None)

    return JSONResponse(content={
        "scheduler": "running",
        "timezone": "Asia/Shanghai",
        "jobs": {
            "product_platforms": product_cron_scheduler.get_next_run_times() if product_cron_scheduler else {},
            "job_configs": job_config_scheduler.get_next_run_times() if job_config_scheduler else {},
        },
    })


@app.get("/health")
async def health_check():
    """Public health check. Returns only overall status to avoid leaking internals.

    Detailed component status is intentionally not exposed; admins should
    inspect logs / /scheduler/status (admin-gated) instead.
    """
    healthy = True

    # Database check
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        healthy = False

    # Redis check
    try:
        redis_client = getattr(app.state, "redis_client", None)
        if redis_client is None:
            healthy = False
        else:
            await redis_client.ping()
    except Exception:
        healthy = False

    return {"status": "healthy" if healthy else "unhealthy"}


if __name__ == "__main__":
    import uvicorn
    # Do NOT use reload=True on Windows — it breaks Playwright subprocess creation
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
