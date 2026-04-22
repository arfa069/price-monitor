"""FastAPI application entry point."""
import asyncio
import sys
from contextlib import asynccontextmanager

# Windows requires ProactorEventLoop for subprocess support (Playwright spawns browser drivers)
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import redis.asyncio as redis
from sqlalchemy import text

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import engine
from app.routers import config, products, alerts, crawl


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup: yield control to the application
    yield
    # Shutdown: close database engine connections gracefully
    await engine.dispose()


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


@app.get("/health")
async def health_check():
    """Health check endpoint with database and Redis checks."""
    checks = {"database": "unknown", "redis": "unknown"}

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

    overall = "healthy" if all(v == "healthy" for v in checks.values()) else "unhealthy"
    return {"status": overall, "checks": checks}


if __name__ == "__main__":
    import uvicorn
    # Do NOT use reload=True on Windows — it breaks Playwright subprocess creation
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000)