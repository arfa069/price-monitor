"""Crawl API router."""
from typing import List
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, delete
from app.database import get_db
from app.models.crawl_log import CrawlLog
from app.models.price_history import PriceHistory
from app.models.product import Product
from app.schemas.crawl_log import CrawlLogResponse
from app.services.crawl import get_active_products

router = APIRouter(prefix="/crawl", tags=["crawl"])

PLATFORM_ADAPTERS = {}


def _get_adapters():
    """Lazy-load adapters to avoid circular imports."""
    global PLATFORM_ADAPTERS
    if not PLATFORM_ADAPTERS:
        from app.platforms import TaobaoAdapter, JDAdapter, AmazonAdapter
        PLATFORM_ADAPTERS.update({
            "taobao": TaobaoAdapter,
            "jd": JDAdapter,
            "amazon": AmazonAdapter,
        })


async def _crawl_one(product_id: int) -> dict:
    """Core crawl logic — runs in the same event loop as the caller."""
    from app.services.crawl import save_price_history, save_crawl_log, check_price_alerts
    from decimal import Decimal

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
                scraped_at = datetime.now(timezone.utc)

                await save_price_history(product_id, price, currency, scraped_at)
                await save_crawl_log(product_id, product.platform, "SUCCESS", price=price, currency=currency)
                await check_price_alerts(product_id, price)

                # Update product title if not set
                new_title = result_data.get("title")
                if new_title:
                    result2 = await db.execute(select(Product).where(Product.id == product_id))
                    prod = result2.scalar_one_or_none()
                    if prod and not prod.title:
                        prod.title = new_title
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
            await save_crawl_log(product_id, product.platform, "ERROR", error_message=str(e))
            raise


@router.post("/start")
async def start_crawl():
    """Manually trigger a crawl for all active products."""
    return JSONResponse(
        content={"message": "Use POST /crawl/crawl-now to trigger crawl"},
        status_code=200,
    )


@router.get("/logs", response_model=List[CrawlLogResponse])
async def get_crawl_logs(
    product_id: int | None = None,
    status: str | None = None,
    hours: int = Query(default=24, ge=1, le=168),
    limit: int = Query(default=100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """Get recent crawl logs."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
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

    Runs directly in FastAPI's async context.
    """
    products = await get_active_products()
    if not products:
        return JSONResponse(content={"status": "no_products", "count": 0})

    results = []
    for product in products:
        result = await _crawl_one(product.id)
        results.append(result)

    success_count = sum(1 for r in results if r.get("status") == "success")
    error_count = sum(1 for r in results if r.get("status") == "error")
    return JSONResponse(content={
        "status": "completed",
        "total": len(products),
        "success": success_count,
        "errors": error_count,
        "details": results,
    })


@router.post("/cleanup")
async def cleanup_old_data(
    retention_days: int = Query(default=365, ge=1, le=3650),
    db: AsyncSession = Depends(get_db),
):
    """Delete price history and crawl logs older than retention period."""
    from app.config import settings

    days = min(retention_days, settings.data_retention_days)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

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
