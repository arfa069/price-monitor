"""User configuration cache with Redis TTL caching.

Avoids repeated DB queries for single-user system config (feishu_webhook_url, etc.).
Cache invalidation happens automatically on config updates via /config endpoints.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import redis.asyncio as redis
from sqlalchemy import select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.user import User

logger = logging.getLogger(__name__)

_redis_client: redis.Redis | None = None

CACHE_KEY = "user:config:1"
CACHE_TTL_SECONDS = 300  # 5 minutes


async def _get_redis() -> redis.Redis:
    """Get or create shared Redis client."""
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.from_url(settings.redis_url_with_password)
    return _redis_client


async def get_cached_user_config(db=None) -> dict[str, Any] | None:
    """Return user config dict from cache, or fetch from DB and cache it.

    Args:
        db: Optional existing async DB session. If None, a new session is created.

    Returns:
        Dict with user config fields, or None if user not found.
    """
    redis_client = await _get_redis()

    # 1. Try cache
    try:
        cached = await redis_client.get(CACHE_KEY)
        if cached:
            return json.loads(cached)
    except Exception:
        logger.exception("Redis cache read failed, falling back to DB")

    # 2. Cache miss — fetch from DB
    if db is not None:
        return await _fetch_and_cache(db, redis_client)

    async with AsyncSessionLocal() as db:
        return await _fetch_and_cache(db, redis_client)


async def _fetch_and_cache(db, redis_client: redis.Redis) -> dict[str, Any] | None:
    """Query DB for user config and write to Redis."""
    result = await db.execute(select(User).where(User.id == 1))
    user = result.scalar_one_or_none()

    if user is None:
        return None

    config = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "feishu_webhook_url": user.feishu_webhook_url or "",
        "data_retention_days": user.data_retention_days,
        "is_active": user.is_active,
    }

    try:
        await redis_client.setex(CACHE_KEY, CACHE_TTL_SECONDS, json.dumps(config))
    except Exception:
        logger.exception("Redis cache write failed")

    return config


async def invalidate_user_config_cache() -> None:
    """Clear the user config cache. Call after any config update."""
    redis_client = await _get_redis()
    try:
        await redis_client.delete(CACHE_KEY)
    except Exception:
        logger.exception("Redis cache invalidate failed")
