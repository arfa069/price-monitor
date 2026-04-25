"""Shared scheduler service for crawl-all logic.

Used by both APScheduler cron job and manual crawl-now endpoint.
Provides a single entry point with concurrency protection.
"""
import asyncio
import logging
import random
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

logger = logging.getLogger(__name__)

# Deferred import to avoid circular dependency
_scheduler_state: dict | None = None

# Concurrency configuration
CONCURRENCY_LIMIT = 3  # Max simultaneous crawls (balance between speed and anti-bot)
CRAWL_INTERVAL_MIN = 2.0  # Seconds between crawls (was 7-12s)
CRAWL_INTERVAL_MAX = 3.0


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CrawlTask:
    """Represents a crawl task with its status and results."""
    task_id: str
    status: TaskStatus = TaskStatus.PENDING
    source: str = "manual"
    total: int = 0
    success: int = 0
    errors: int = 0
    details: list = field(default_factory=list)
    reason: str | None = None
    created_at: float = field(default_factory=lambda: asyncio.get_event_loop().time())


# In-memory task storage
_crawl_tasks: dict[str, CrawlTask] = {}


def _set_scheduler_state(state: dict) -> None:
    """Called once by main.py lifespan startup."""
    global _scheduler_state
    _scheduler_state = state


def get_task(task_id: str) -> CrawlTask | None:
    """Get task by ID."""
    return _crawl_tasks.get(task_id)


def create_task(source: Literal["cron", "manual"]) -> CrawlTask:
    """Create a new crawl task and return its info."""
    task_id = str(uuid.uuid4())[:8]
    task = CrawlTask(task_id=task_id, source=source)
    _crawl_tasks[task_id] = task
    return task


async def _crawl_one_with_semaphore(
    product_id: int, semaphore: asyncio.Semaphore, from_app: bool
) -> dict:
    """Crawl a single product with semaphore-controlled concurrency."""
    async with semaphore:
        from app.routers.crawl import _crawl_one

        result = await _crawl_one(product_id)
        await asyncio.sleep(random.uniform(CRAWL_INTERVAL_MIN, CRAWL_INTERVAL_MAX))
        return result


async def _run_crawl_task(task: CrawlTask) -> None:
    """Execute the actual crawl and update task status."""
    task.status = TaskStatus.RUNNING
    logger.info(f"Task {task.task_id}: started (source={task.source})")

    try:
        from app.services.crawl import get_active_products

        products = await get_active_products()
        if not products:
            logger.info(f"Task {task.task_id}: no active products")
            task.status = TaskStatus.COMPLETED
            task.reason = "no_active_products"
            return

        task.total = len(products)
        product_ids = [p.id for p in products]
        semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

        tasks = [
            _crawl_one_with_semaphore(pid, semaphore, True) for pid in product_ids
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.exception("Crawl failed for product %d", product_ids[i])
                processed_results.append(
                    {"status": "error", "product_id": product_ids[i], "error": str(result)}
                )
            else:
                processed_results.append(result)

        task.success = sum(1 for r in processed_results if r.get("status") == "success")
        task.errors = sum(1 for r in processed_results if r.get("status") == "error")
        task.details = processed_results
        task.status = TaskStatus.COMPLETED
        logger.info(f"Task {task.task_id}: completed ({task.success} success, {task.errors} errors)")

    except Exception as e:
        logger.exception(f"Task {task.task_id}: failed")
        task.status = TaskStatus.FAILED
        task.reason = str(e)
    finally:
        # Clean up shared browser context
        if browser_context:
            try:
                from app.routers.crawl import _cleanup_shared_browser
                _cleanup_shared_browser(browser_context)
            except Exception:
                pass


async def crawl_all_products(source: Literal["cron", "manual"], background: bool = True) -> dict:
    """Start crawl all active products with concurrency protection.

    Uses a shared Semaphore to prevent overlapping executions from
    both cron-triggered and manually-triggered crawl operations.

    Args:
        source: "cron" for APScheduler-triggered, "manual" for HTTP endpoint
        background: If True, run crawl in background and return task ID immediately.
                   If False, wait for completion (for cron jobs).

    Returns:
        dict with task_id (if background=True) or full results
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

    # Create task and start background execution
    task = create_task(source)

    if background:
        # Create background task - it will acquire the lock when it runs
        asyncio.create_task(_run_crawl_in_lock(task, crawl_lock))
        return {
            "status": "pending",
            "task_id": task.task_id,
            "source": source,
        }

    # Synchronous execution (for cron jobs)
    async with crawl_lock:
        logger.info("Crawl started (source=%s, concurrency=%d)", source, CONCURRENCY_LIMIT)
        try:
            from app.services.crawl import get_active_products

            products = await get_active_products()
            if not products:
                logger.info("No active products to crawl")
                return {"status": "completed", "total": 0, "success": 0, "errors": 0}

            product_ids = [p.id for p in products]
            semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

            tasks = [
                _crawl_one_with_semaphore(pid, semaphore, True) for pid in product_ids
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.exception("Crawl failed for product %d", product_ids[i])
                    processed_results.append(
                        {"status": "error", "product_id": product_ids[i], "error": str(result)}
                    )
                else:
                    processed_results.append(result)

            success_count = sum(
                1 for r in processed_results if r.get("status") == "success"
            )
            error_count = sum(1 for r in processed_results if r.get("status") == "error")
            return {
                "status": "completed",
                "total": len(products),
                "success": success_count,
                "errors": error_count,
                "details": processed_results,
                "source": source,
            }
        except Exception:
            logger.exception("Crawl failed (source=%s)", source)
            return {"status": "error", "reason": "internal_error", "source": source}


async def _run_crawl_in_lock(task: CrawlTask, crawl_lock: asyncio.Semaphore) -> None:
    """Run crawl task with lock protection."""
    try:
        async with crawl_lock:
            await _run_crawl_task(task)
    finally:
        # Clean up shared browsers after task completes
        await _cleanup_all_shared_browsers()


async def _cleanup_all_shared_browsers() -> None:
    """Close all shared browser instances after crawl task."""
    from app.platforms import AmazonAdapter, JDAdapter, TaobaoAdapter

    for adapter_class in [TaobaoAdapter, JDAdapter, AmazonAdapter]:
        try:
            await adapter_class._close_shared_browser()
        except Exception:
            pass
