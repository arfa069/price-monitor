"""Crawl API router."""
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, get_db
from app.models.crawl_log import CrawlLog
from app.models.price_history import PriceHistory
from app.models.product import Product
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
    db: AsyncSession = Depends(get_db),
):
    """Get recent crawl logs."""
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    query = select(CrawlLog).where(CrawlLog.timestamp >= cutoff)

    if product_id is not None:
        query = query.where(CrawlLog.product_id == product_id)
    if status is not None:
        query = query.where(CrawlLog.status == status.upper())

    query = query.order_by(desc(CrawlLog.timestamp)).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/crawl-now")
async def crawl_now():
    """Crawl all active products immediately.

    Uses the shared scheduler service for concurrency protection.
    One product's failure does not affect others.
    """
    from app.services.scheduler_service import crawl_all_products

    result = await crawl_all_products(source="manual")
    if result["status"] == "skipped":
        return JSONResponse(content={"status": "skipped", "reason": result["reason"]})
    if result["status"] == "error":
        return JSONResponse(content={"status": "error", "reason": result["reason"]}, status_code=500)

    return JSONResponse(content={
        "status": result["status"],
        "total": result.get("total", 0),
        "success": result.get("success", 0),
        "errors": result.get("errors", 0),
        "details": result.get("details", []),
    })


@router.post("/cleanup")
async def cleanup_old_data(
    retention_days: int = Query(default=365, ge=1, le=3650),
    db: AsyncSession = Depends(get_db),
):
    """Delete price history and crawl logs older than retention period."""
    from app.config import settings

    days = min(retention_days, settings.data_retention_days)
    cutoff = datetime.now(UTC) - timedelta(days=days)

    # Count before deleting
    price_count = await db.execute(
        select(CrawlLog.id).where(CrawlLog.timestamp < cutoff)
    )
    deleted_logs = len(list((await db.execute(price_count)).scalars().all()))

    price_hist = await db.execute(
        select(PriceHistory.id).where(PriceHistory.scraped_at < cutoff)
    )
    deleted_prices = len(list((await db.execute(price_hist)).scalars().all()))

    # Execute deletes
    await db.execute(delete(CrawlLog).where(CrawlLog.timestamp < cutoff))
    await db.execute(delete(PriceHistory).where(PriceHistory.scraped_at < cutoff))
    await db.commit()

    return JSONResponse(content={
        "status": "completed",
        "deleted_crawl_logs": deleted_logs,
        "deleted_price_history": deleted_prices,
        "cutoff_date": cutoff.isoformat(),
        "retention_days": days,
    })
