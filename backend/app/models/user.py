"""User configuration model."""
from sqlalchemy import Boolean, Column, Integer, String

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """User model for authentication."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Legacy fields (for backward compatibility)
    feishu_webhook_url = Column(String, nullable=True)
    data_retention_days = Column(Integer, nullable=False, default=365)

    @property
    def is_authenticated(self) -> bool:
        """Return True if user is active."""
        return self.is_active
