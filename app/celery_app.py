"""Celery application configuration."""
from datetime import timedelta

from celery import Celery
from app.config import settings

celery_app = Celery(
    "price_monitor",
    broker=settings.redis_url_with_password,
    backend=settings.redis_url_with_password,
    include=["app.tasks.crawl", "app.tasks.cleanup"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # 4 minutes soft limit
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Rate limiting: max 10 crawl requests per minute per worker
    # to avoid overwhelming target websites
    task_annotations={
        "app.tasks.crawl.crawl_product": {"rate_limit": "10/m"},
    },
)

# Beat schedule for periodic crawl
celery_app.conf.beat_schedule = {
    "periodic-crawl": {
        "task": "app.tasks.crawl.crawl_all_products",
        "schedule": timedelta(hours=settings.crawl_frequency_hours),
    },
    "daily-cleanup": {
        "task": "app.tasks.cleanup.cleanup_old_data",
        "schedule": timedelta(days=1),
    },
}