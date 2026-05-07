"""Session model for device tracking."""
from datetime import UTC, datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.models.base import Base, TimestampMixin


class Session(Base, TimestampMixin):
    """Session model for tracking user login devices."""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    device = Column(String(255))
    ip_address = Column(String(45))
    last_active_at = Column(DateTime(timezone=True), nullable=False, default=datetime.now(UTC))
