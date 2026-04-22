"""Crawl log model for tracking crawler activity."""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base import Base


class CrawlLog(Base):
    """Log of crawl attempts for debugging."""
    __tablename__ = "crawl_logs"
    __table_args__ = (
        Index("ix_crawl_logs_product_timestamp", "product_id", "timestamp"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    platform = Column(String(20), nullable=True)
    status = Column(String(20), nullable=True)  # SUCCESS, ERROR
    price = Column(Numeric(12, 2), nullable=True)
    currency = Column(String(3), nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False)
    error_message = Column(Text, nullable=True)

    # Relationships
    product = relationship("Product", back_populates="crawl_logs")