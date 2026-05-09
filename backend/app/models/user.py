"""User configuration model."""
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, Column, DateTime, Integer, String

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """User model for authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    role = Column(String(20), nullable=False, default="user")
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # WeChat login fields
    wechat_openid = Column(String(64), unique=True, nullable=True, index=True)
    wechat_union_id = Column(String(64), nullable=True)
    wechat_bind_at = Column(DateTime(timezone=True), nullable=True)

    # Legacy fields (for backward compatibility)
    feishu_webhook_url = Column(String, nullable=True)
    data_retention_days = Column(Integer, nullable=False, default=365)

    @property
    def is_authenticated(self) -> bool:
        """Return True if user is active and not deleted."""
        return self.is_active and self.deleted_at is None

    @property
    def is_admin(self) -> bool:
        """Return True if user has admin role."""
        return self.role in ("admin", "super_admin")

    @property
    def is_deleted(self) -> bool:
        """Return True if user is soft deleted."""
        return self.deleted_at is not None
