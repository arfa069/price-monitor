"""Price history model."""
from sqlalchemy import Column, Integer, Numeric, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base import Base


class PriceHistory(Base):
    """Historical price records for a product."""
    __tablename__ = "price_history"
    __table_args__ = (
        Index("ix_price_history_product_scraped", "product_id", "scraped_at"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    price = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="CNY")
    scraped_at = Column(DateTime(timezone=True), nullable=False)
    source_site = Column(String(50), nullable=True)
    page_hash = Column(String, nullable=True)

    # Relationships
    product = relationship("Product", back_populates="price_history")