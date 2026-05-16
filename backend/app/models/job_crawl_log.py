"""Job crawl log model for tracking BOSS Zhipin crawl activity."""
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, Integer, String, Text

from app.models.base import Base, TimestampMixin


class JobCrawlLog(Base, TimestampMixin):
    """Log of BOSS job crawl attempts."""

    __tablename__ = "jobs_crawl_logs"
    __table_args__ = (
        Index("ix_jobs_crawl_logs_config_scraped", "search_config_id", "scraped_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    search_config_id = Column(
        Integer, ForeignKey("jobs_search_configs.id", ondelete="CASCADE"), nullable=False
    )
    status = Column(String(20), nullable=False)  # SUCCESS, ERROR
    new_jobs_count = Column(Integer, nullable=True)
    total_jobs_count = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    scraped_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))
