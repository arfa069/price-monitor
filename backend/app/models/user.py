"""User configuration model."""
from sqlalchemy import Column, Integer, SmallInteger, String, Text

from app.models.base import Base, TimestampMixin


class User(Base, TimestampMixin):
    """Single-user configuration for the price monitor."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String, nullable=False, default="default")
    feishu_webhook_url = Column(Text, nullable=True)
    data_retention_days = Column(SmallInteger, nullable=False, default=365)
