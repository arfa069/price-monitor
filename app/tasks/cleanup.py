"""Data retention cleanup task."""
from datetime import datetime, timedelta, timezone

from celery import shared_task
from sqlalchemy import delete, select

from app.config import settings
from app.database import AsyncSessionLocal
from app.models.price_history import PriceHistory
from app.models.crawl_log import CrawlLog


@shared_task
def cleanup_old_data() -> dict:
    """Delete price history and crawl logs older than retention period.

    Runs daily via Celery Beat.
    Keeps data for data_retention_days (default 365).
    """
    import asyncio

    async def _cleanup():
        retention_days = settings.data_retention_days
        cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)

        async with AsyncSessionLocal() as db:
            # Count before deleting (rowcount unreliable with asyncpg/async DELETE)
            price_count_result = await db.execute(
                select(PriceHistory.id).where(PriceHistory.scraped_at < cutoff)
            )
            deleted_prices = len(price_count_result.scalars().all())

            log_count_result = await db.execute(
                select(CrawlLog.id).where(CrawlLog.timestamp < cutoff)
            )
            deleted_logs = len(log_count_result.scalars().all())

            # Execute deletes
            await db.execute(delete(PriceHistory).where(PriceHistory.scraped_at < cutoff))
            await db.execute(delete(CrawlLog).where(CrawlLog.timestamp < cutoff))
            await db.commit()

            return {
                "status": "completed",
                "deleted_price_history": deleted_prices,
                "deleted_crawl_logs": deleted_logs,
                "cutoff_date": cutoff.isoformat(),
                "retention_days": retention_days,
            }

    loop = asyncio.get_event_loop()
    return loop.run_until_complete(_cleanup())
