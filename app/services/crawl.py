"""Crawl-related service functions: price history, logs, and alert checks."""
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import List

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.product import Product
from app.models.price_history import PriceHistory
from app.models.crawl_log import CrawlLog
from app.models.alert import Alert
from app.models.user import User
from app.services.notification import send_feishu_notification

logger = logging.getLogger(__name__)


async def get_active_products() -> List[Product]:
    """Fetch all active products from database."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Product).where(Product.user_id == 1, Product.active)
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
    """Check and trigger price drop alerts.

    Compares the latest two price history records. If drop >= threshold_percent,
    sends a Feishu notification via the product owner's webhook URL.
    """
    async with AsyncSessionLocal() as db:
        # Get all active alerts for this product
        result = await db.execute(
            select(Alert).where(Alert.product_id == product_id, Alert.active)
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
        previous_price = price_records[1].price
        new_price = current_price

        for alert in alerts:
            if alert.threshold_percent is None:
                continue

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
                        logger.exception(
                            "Failed to send price drop notification for product %s",
                            product_id,
                        )
