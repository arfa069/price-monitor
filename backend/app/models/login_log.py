"""Login history model."""
from datetime import UTC, datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.models.base import Base, TimestampMixin


class LoginLog(Base):
    """Login history for user account security."""
    __tablename__ = "login_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    ip_address = Column(String(45))
    user_agent = Column(String(512))
    created_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now(UTC))
