"""Permission model."""
from sqlalchemy import Column, Integer, String

from app.models.base import Base, TimestampMixin


class Permission(Base, TimestampMixin):
    """Permission model for RBAC."""
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(255))