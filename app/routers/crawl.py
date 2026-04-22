"""Crawl API router."""
from typing import List
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.database import get_db
from app.models.crawl_log import CrawlLog
from app.schemas.crawl_log import CrawlLogResponse
from app.celery_app import celery_app

router = APIRouter(prefix="/crawl", tags=["crawl"])


@router.post("/start")
async def start_crawl():
    """Manually trigger a crawl for all active products."""
    # Use send_task to dispatch Celery task from async context
    task = celery_app.send_task("app.tasks.crawl.crawl_all_products")
    return {"message": "Crawl started", "task_id": task.id}


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