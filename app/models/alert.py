"""Alert configuration model."""
from sqlalchemy import Column, Integer, Numeric, String, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.models.base import Base, TimestampMixin


class Alert(Base, TimestampMixin):
    """Price drop alert configuration."""
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_product_active", "product_id", "active"),
        Index("ix_alerts_active", "active"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    alert_type = Column(String(20), nullable=False, default="price_drop")
    threshold_percent = Column(Numeric(5, 2), nullable=True)  # e.g., 5.00 for 5%
    last_notified_at = Column(DateTime, nullable=True)
    last_notified_price = Column(Numeric(12, 2), nullable=True)
    active = Column(Boolean, nullable=False, default=True)

    # Relationships
    product = relationship("Product", back_populates="alerts")