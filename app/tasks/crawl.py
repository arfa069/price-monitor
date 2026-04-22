"""Crawl tasks for Celery."""
import asyncio
from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from celery import shared_task
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.product import Product
from app.models.price_history import PriceHistory
from app.models.crawl_log import CrawlLog
from app.models.alert import Alert
from app.models.user import User
from app.platforms import TaobaoAdapter, JDAdapter, AmazonAdapter
from app.services.notification import send_feishu_notification

PLATFORM_ADAPTERS = {
    "taobao": TaobaoAdapter,
    "jd": JDAdapter,
    "amazon": AmazonAdapter,
}


async def get_active_products() -> List[Product]:
    """Fetch all active products from database."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Product).where(Product.user_id == 1, Product.active == True)
        )
        return list(result.scalars().all())


async def get_user_config() -> User | None:
    """Fetch user configuration."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.id == 1))
        return result.scalar_one_or_none()


async def save_price_history(
    product_id: int,
    price: Decimal,
    currency: str,
    scraped_at: datetime,
) -> None:
    """Save price to history."""
    async with AsyncSessionLocal() as db:
        history = PriceHistory(
            product_id=product_id,
            price=price,
            currency=currency,
            scraped_at=scraped_at,
        )
        db.add(history)
        await db.commit()


async def save_crawl_log(
    product_id: int,
    platform: str,
    status: str,
    price: Decimal | None = None,
    currency: str | None = None,
    error_message: str | None = None,
) -> None:
    """Save crawl log entry."""
    async with AsyncSessionLocal() as db:
        log = CrawlLog(
            product_id=product_id,
            platform=platform,
            status=status,
            price=price,
            currency=currency,
            timestamp=datetime.now(timezone.utc),
            error_message=error_message,
        )
        db.add(log)
        await db.commit()


async def check_price_alerts(product_id: int, current_price: Decimal) -> None:
    """Check and trigger price drop alerts."""
    async with AsyncSessionLocal() as db:
        # Get all active alerts for this product
        result = await db.execute(
            select(Alert).where(Alert.product_id == product_id, Alert.active == True)
        )
        alerts = result.scalars().all()

        if not alerts:
            return

        # Get product info
        product_result = await db.execute(select(Product).where(Product.id == product_id))
        product = product_result.scalar_one_or_none()

        if not product:
            return

        # Get user config for webhook URL (via product's user_id)
        user_result = await db.execute(select(User).where(User.id == product.user_id))
        user = user_result.scalar_one_or_none()

        if not user or not user.feishu_webhook_url:
            return

        # Get latest price from history
        latest_result = await db.execute(
            select(PriceHistory)
            .where(PriceHistory.product_id == product_id)
            .order_by(PriceHistory.scraped_at.desc())
            .limit(2)
        )
        price_records = list(latest_result.scalars().all())

        if len(price_records) < 2:
            return

        # Compare with previous price
        # price_records[0] = most recent (may equal current_price if same transaction)
        # price_records[1] = previous price for comparison
        previous_price = price_records[1].price
        new_price = current_price

        for alert in alerts:
            if alert.threshold_percent is None:
                continue

            # Calculate percentage drop
            if previous_price > 0:
                drop_percent = ((previous_price - new_price) / previous_price) * 100

                if drop_percent >= alert.threshold_percent:
                    # Check if we already notified for this price level
                    if (
                        alert.last_notified_price is not None
                        and alert.last_notified_price <= new_price
                    ):
                        continue

                    # Send notification
                    message = (
                        f"Price Drop Alert: {product.title or product.url}\n"
                        f"Platform: {product.platform}\n"
                        f"Old Price: {previous_price} {price_records[1].currency}\n"
                        f"New Price: {new_price} {price_records[1].currency}\n"
                        f"Drop: {drop_percent:.2f}%\n"
                        f"Link: {product.url}"
                    )

                    try:
                        await send_feishu_notification(
                            user.feishu_webhook_url,
                            message,
                        )

                        # Update alert
                        alert.last_notified_at = datetime.now(timezone.utc)
                        alert.last_notified_price = new_price
                        await db.commit()
                    except Exception:
                        pass


@shared_task(bind=True, max_retries=3)
def crawl_product(self, product_id: int) -> dict:
    """Crawl a single product."""
    # Run async code in sync context
    loop = asyncio.get_event_loop()

    async def _crawl():
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Product).where(Product.id == product_id)
            )
            product = result.scalar_one_or_none()

            if not product or not product.active:
                return {"status": "skipped", "product_id": product_id}

            # Get appropriate adapter
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
                # Crawl the product
                result_data = await adapter.crawl(product.url)

                if result_data.get("success"):
                    price = Decimal(str(result_data["price"]))
                    currency = result_data.get("currency", "CNY")
                    scraped_at = datetime.now(timezone.utc)

                    # Save price history
                    await save_price_history(product_id, price, currency, scraped_at)

                    # Save crawl log
                    await save_crawl_log(
                        product_id,
                        product.platform,
                        "SUCCESS",
                        price=price,
                        currency=currency,
                    )

                    # Check for price drop alerts
                    await check_price_alerts(product_id, price)

                    return {
                        "status": "success",
                        "product_id": product_id,
                        "price": float(price),
                    }
                else:
                    await save_crawl_log(
                        product_id,
                        product.platform,
                        "ERROR",
                        error_message=result_data.get("error", "Unknown error"),
                    )
                    return {"status": "error", "product_id": product_id}

            except Exception as e:
                await save_crawl_log(
                    product_id,
                    product.platform,
                    "ERROR",
                    error_message=str(e),
                )
                raise self.retry(exc=e, countdown=60)

    return loop.run_until_complete(_crawl())


@shared_task
def crawl_all_products() -> dict:
    """Crawl all active products using celery.group() for concurrent execution."""
    loop = asyncio.get_event_loop()

    async def _crawl_all():
        from celery import group

        products = await get_active_products()

        if not products:
            return {"status": "no_products", "count": 0}

        # Use celery.group() to dispatch all crawl_product tasks concurrently.
        # group(...) returns a GroupResult; .get() waits for all tasks to complete.
        job = group(crawl_product.s(product.id) for product in products)
        group_result = job.apply_async()

        # Wait for all results with a single aggregate timeout.
        # Each task has its own 300s time limit; the group timeout is 5min total.
        try:
            results = group_result.get(timeout=300)
        except Exception as e:
            return {"status": "error", "error": str(e)}

        success_count = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "success")
        error_count = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "error")

        return {
            "status": "completed",
            "total": len(products),
            "success": success_count,
            "errors": error_count,
        }

    return loop.run_until_complete(_crawl_all())