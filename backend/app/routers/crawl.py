"""Crawl API router."""
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, get_db
from app.models.crawl_log import CrawlLog
from app.models.price_history import PriceHistory
from app.models.product import Product
from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.crawl_log import CrawlLogResponse

router = APIRouter(prefix="/crawl", tags=["crawl"])

PLATFORM_ADAPTERS = {}


def _get_adapters():
    """Lazy-load adapters to avoid circular imports."""
    global PLATFORM_ADAPTERS
    if not PLATFORM_ADAPTERS:
        from app.platforms import AmazonAdapter, JDAdapter, TaobaoAdapter
        PLATFORM_ADAPTERS.update({
            "taobao": TaobaoAdapter,
            "jd": JDAdapter,
            "amazon": AmazonAdapter,
        })


async def _crawl_one(product_id: int) -> dict:
    """Core crawl logic — runs in the same event loop as the caller."""
    from decimal import Decimal

    from app.services.crawl import (
        check_price_alerts,
        save_crawl_log,
        save_price_history,
    )

    _get_adapters()

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()

        if not product or not product.active:
            return {"status": "skipped", "product_id": product_id}

        adapter_class = PLATFORM_ADAPTERS.get(product.platform)
        if not adapter_class:
            await save_crawl_log(
                product_id,
                product.platform,
                "ERROR",
                error_message=f"Unknown platform: {product.platform}",
            )
            return {"status": "error", "product_id": product_id}

        adapter = adapter_class()

        try:
            result_data = await adapter.crawl(product.url)

            if result_data.get("success"):
                price = Decimal(str(result_data["price"]))
                currency = result_data.get("currency", "CNY")
                scraped_at = datetime.now(UTC)

                await save_price_history(product_id, price, currency, scraped_at)
                await save_crawl_log(product_id, product.platform, "SUCCESS", price=price, currency=currency)
                await check_price_alerts(product_id, price)

                # Update product title if not set
                new_title = result_data.get("title")
                if new_title and not product.title:
                    product.title = new_title
                    await db.commit()

                return {"status": "success", "product_id": product_id, "price": float(price)}
            else:
                await save_crawl_log(
                    product_id,
                    product.platform,
                    "ERROR",
                    error_message=result_data.get("error", "Unknown error"),
                )
                return {"status": "error", "product_id": product_id}

        except Exception as e:
            platform_name = product.platform if product else "unknown"
            await save_crawl_log(product_id, platform_name, "ERROR", error_message=str(e))
            return {"status": "error", "product_id": product_id, "error": str(e)}


@router.get("/logs", response_model=list[CrawlLogResponse])
async def get_crawl_logs(
    product_id: int | None = None,
    status: str | None = None,
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=100, ge=1, le=1000),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get recent crawl logs."""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    query = select(CrawlLog).where(CrawlLog.timestamp >= cutoff)

    if product_id is not None:
        query = query.where(CrawlLog.product_id == product_id)
    if status is not None:
        query = query.where(CrawlLog.status == status.upper())

    query = query.order_by(desc(CrawlLog.timestamp)).limit(limit)
    result = await db.execute(query)
    logs = result.scalars().all()
    # Filter by user_id via product relationship
    user_product_ids_result = await db.execute(
        select(Product.id).where(Product.user_id == current_user.id)
    )
    user_product_ids = set(row[0] for row in user_product_ids_result.fetchall())
    return [log for log in logs if log.product_id in user_product_ids]


@router.post("/crawl-now")
async def crawl_now(
    current_user: User = Depends(get_current_user),
):
    """Start crawling all active products immediately.

    Returns immediately with a task_id. Poll /crawl/status/{task_id} for progress.
    """
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    from app.services.scheduler_service import crawl_all_products

    result = await crawl_all_products(source="manual", background=True)

    if result["status"] == "skipped":
        return JSONResponse(content={"status": "skipped", "reason": result["reason"]}, status_code=409)
    if result["status"] == "error":
        return JSONResponse(content={"status": "error", "reason": result["reason"]}, status_code=500)

    return JSONResponse(content={
        "status": "pending",
        "task_id": result["task_id"],
        "message": "爬取任务已启动，请通过 /crawl/status/{task_id} 查询进度",
    })


@router.get("/status/{task_id}")
async def get_crawl_status(task_id: str):
    """Get the status of a crawl task."""
    from app.services.scheduler_service import get_task

    task = get_task(task_id)
    if not task:
        return JSONResponse(content={"status": "error", "reason": "task_not_found"}, status_code=404)

    return JSONResponse(content={
        "task_id": task.task_id,
        "status": task.status.value,
        "total": task.total,
        "success": task.success,
        "errors": task.errors,
        "reason": task.reason,
    })


@router.get("/result/{task_id}")
async def get_crawl_result(task_id: str):
    """Get the final result of a completed crawl task."""
    from app.services.scheduler_service import get_task, TaskStatus

    task = get_task(task_id)
    if not task:
        return JSONResponse(content={"status": "error", "reason": "task_not_found"}, status_code=404)

    if task.status == TaskStatus.PENDING or task.status == TaskStatus.RUNNING:
        return JSONResponse(content={
            "status": task.status.value,
            "task_id": task.task_id,
            "total": task.total,
            "success": task.success,
            "errors": task.errors,
        }, status_code=202)

    if task.status == TaskStatus.FAILED:
        return JSONResponse(content={
            "status": "error",
            "task_id": task.task_id,
            "reason": task.reason,
        }, status_code=500)

    # Completed
    return JSONResponse(content={
        "status": "completed",
        "task_id": task.task_id,
        "total": task.total,
        "success": task.success,
        "errors": task.errors,
        "details": task.details,
    })


@router.post("/cleanup")
async def cleanup_old_data(
    retention_days: int = Query(default=365, ge=1, le=3650),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete price history and crawl logs older than retention period."""
    if not current_user:
        raise HTTPException(status_code=401, detail="请先登录")
    from app.config import settings

    days = min(retention_days, settings.data_retention_days)
    cutoff = datetime.now(UTC) - timedelta(days=days)

    # Get user's product IDs for filtering
    user_products_result = await db.execute(
        select(Product.id).where(Product.user_id == current_user.id)
    )
    user_product_ids = [row[0] for row in user_products_result.fetchall()]

    if not user_product_ids:
        return JSONResponse(content={
            "status": "completed",
            "deleted_crawl_logs": 0,
            "deleted_price_history": 0,
            "cutoff_date": cutoff.isoformat(),
            "retention_days": days,
        })

    # Count before deleting
    log_count_result = await db.execute(
        select(CrawlLog.id).where(
            CrawlLog.timestamp < cutoff,
            CrawlLog.product_id.in_(user_product_ids)
        )
    )
    deleted_logs = len(list(log_count_result.scalars().all()))

    price_count_result = await db.execute(
        select(PriceHistory.id).where(
            PriceHistory.scraped_at < cutoff,
            PriceHistory.product_id.in_(user_product_ids)
        )
    )
    deleted_prices = len(list(price_count_result.scalars().all()))

    # Execute deletes (only user's data)
    await db.execute(
        delete(CrawlLog).where(
            CrawlLog.timestamp < cutoff,
            CrawlLog.product_id.in_(user_product_ids)
        )
    )
    await db.execute(
        delete(PriceHistory).where(
            PriceHistory.scraped_at < cutoff,
            PriceHistory.product_id.in_(user_product_ids)
        )
    )
    await db.commit()

    return JSONResponse(content={
        "status": "completed",
        "deleted_crawl_logs": deleted_logs,
        "deleted_price_history": deleted_prices,
        "cutoff_date": cutoff.isoformat(),
        "retention_days": days,
    })
