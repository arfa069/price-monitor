"""Shared scheduler service for crawl-all logic.

Used by both APScheduler cron job and manual crawl-now endpoint.
Provides a single entry point with concurrency protection.
"""
import asyncio
import logging
import random
from typing import Literal

logger = logging.getLogger(__name__)

# Deferred import to avoid circular dependency
_scheduler_state: dict | None = None


def _set_scheduler_state(state: dict) -> None:
    """Called once by main.py lifespan startup."""
    global _scheduler_state
    _scheduler_state = state


async def crawl_all_products(source: Literal["cron", "manual"]) -> dict:
    """Crawl all active products with concurrency protection.

    Uses a shared Semaphore to prevent overlapping executions from
    both cron-triggered and manually-triggered crawl operations.

    Args:
        source: "cron" for APScheduler-triggered, "manual" for HTTP endpoint

    Returns:
        dict with status, counts, and per-product results
    """
    if _scheduler_state is None:
        logger.error("Scheduler state not initialized")
        return {"status": "error", "reason": "scheduler_not_initialized"}

    crawl_lock: asyncio.Semaphore = _scheduler_state.get("crawl_lock")
    if crawl_lock is None:
        logger.error("crawl_lock not initialized")
        return {"status": "error", "reason": "lock_not_initialized"}

    if crawl_lock.locked():
        logger.warning("Crawl skipped: another crawl is in progress (source=%s)", source)
        return {
            "status": "skipped",
            "reason": "another_crawl_in_progress",
            "source": source,
        }

    async with crawl_lock:
        logger.info("Crawl started (source=%s)", source)
        try:
            from app.services.crawl import get_active_products
            products = await get_active_products()
            if not products:
                logger.info("No active products to crawl")
                return {"status": "completed", "total": 0, "success": 0, "errors": 0}

            from app.routers.crawl import _crawl_one
            results = []
            for product in products:
                result = await _crawl_one(product.id)
                results.append(result)
                await asyncio.sleep(random.uniform(7, 12))

            success_count = sum(1 for r in results if r.get("status") == "success")
            error_count = sum(1 for r in results if r.get("status") == "error")
            return {
                "status": "completed",
                "total": len(products),
                "success": success_count,
                "errors": error_count,
                "details": results,
                "source": source,
            }
        except Exception:
            logger.exception("Crawl failed (source=%s)", source)
            return {"status": "error", "reason": "internal_error", "source": source}
