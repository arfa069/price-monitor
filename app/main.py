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
from sqlalchemy import text

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine, AsyncSessionLocal
from app.routers import config, products, alerts, crawl
from app.models.user import User
from sqlalchemy import select

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    await _start_scheduler(app)
    yield
    # Shutdown: stop scheduler gracefully
    await _stop_scheduler(app)
    # Close database engine connections
    await engine.dispose()


async def _start_scheduler(app: FastAPI) -> None:
    """Initialize APScheduler with AsyncIOScheduler and register cron job from DB config."""
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    from apscheduler.triggers.cron import CronTrigger
    import zoneinfo

    # Initialize concurrency lock
    app.state.crawl_lock = asyncio.Semaphore(1)

    # Register state with scheduler service (shared by cron and manual crawl)
    from app.services.scheduler_service import _set_scheduler_state
    _set_scheduler_state({"crawl_lock": app.state.crawl_lock})

    # Read user config
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == 1))
        user = result.scalar_one_or_none()

    scheduler = AsyncIOScheduler(timezone="UTC", job_defaults={"coalesce": True, "max_instances": 1})
    app.state.scheduler = scheduler

    if user and user.crawl_cron:
        job_id = "crawl_cron_job"
        try:
            tz = zoneinfo.ZoneInfo(user.crawl_timezone or "Asia/Shanghai")
            # Import the trigger function lazily to avoid circular dependency
            from app.routers.config import _trigger_crawl_all
            scheduler.add_job(
                _trigger_crawl_all,
                trigger=CronTrigger.from_crontab(user.crawl_cron, timezone=tz),
                id=job_id,
                name="Crawl all active products",
                replace_existing=True,
                max_instances=1,
            )
            logger.info(
                "Registered cron job %s with schedule '%s' (tz=%s)",
                job_id, user.crawl_cron, user.crawl_timezone or "Asia/Shanghai",
            )
        except Exception:
            logger.exception("Failed to register initial cron job from DB config")
    else:
        if user is None:
            logger.info("No user config found, skipping scheduler registration")
        else:
            logger.info("No crawl_cron configured, skipping scheduler registration")

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
    "http://localhost:5173",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(config.router)
app.include_router(products.router)
app.include_router(alerts.router)
app.include_router(crawl.router)

# Scheduler status endpoint
@app.get("/scheduler/status", tags=["scheduler"])
async def get_scheduler_status():
    """Get APScheduler status and next run time."""
    scheduler = getattr(app.state, "scheduler", None)

    if scheduler is None:
        return JSONResponse(
            status_code=503,
            content={"scheduler": "not_started"},
        )

    job_id = "crawl_cron_job"
    job = scheduler.get_job(job_id)

    if job is None:
        return JSONResponse(content={
            "scheduler": "running",
            "job_registered": False,
            "next_run_at": None,
            "cron_expression": None,
        })

    from app.database import AsyncSessionLocal
    from app.models.user import User
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == 1))
        user = result.scalar_one_or_none()

    return JSONResponse(content={
        "scheduler": "running",
        "job_registered": True,
        "next_run_at": job.next_run_time.isoformat() if job.next_run_time else None,
        "cron_expression": user.crawl_cron if user else None,
        "timezone": user.crawl_timezone if user else "Asia/Shanghai",
    })


@app.get("/health")
async def health_check():
    """Health check endpoint with database and Redis checks."""
    checks = {"database": "unknown", "redis": "unknown", "scheduler": "unknown"}

    # Database check
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        checks["database"] = "healthy"
    except Exception as e:
        checks["database"] = f"unhealthy: {e}"

    # Redis check
    try:
        redis_client = redis.from_url(settings.redis_url_with_password)
        await redis_client.ping()
        await redis_client.aclose()
        checks["redis"] = "healthy"
    except Exception as e:
        checks["redis"] = f"unhealthy: {e}"

    # Scheduler check
    scheduler = getattr(app.state, "scheduler", None)
    if scheduler is not None and scheduler.running:
        checks["scheduler"] = "running"
    else:
        checks["scheduler"] = "not_running"

    overall = "healthy" if all(v == "healthy" or v == "running" or v == "not_running" for v in checks.values()) else "unhealthy"
    return {"status": overall, "checks": checks}


if __name__ == "__main__":
    import uvicorn
    # Do NOT use reload=True on Windows — it breaks Playwright subprocess creation
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)
