"""Product model for tracked items."""
from sqlalchemy import Column, Integer, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Product(Base, TimestampMixin):
    """Tracked product on an e-commerce platform."""
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    platform = Column(String(20), nullable=False)  # 'taobao', 'jd', 'amazon'
    url = Column(Text, nullable=False)
    platform_product_id = Column(String, nullable=True)
    title = Column(String, nullable=True)
    active = Column(Boolean, nullable=False, default=True)

    # Relationships
    price_history = relationship("PriceHistory", back_populates="product", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="product", cascade="all, delete-orphan")
    crawl_logs = relationship("CrawlLog", back_populates="product")