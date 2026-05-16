"""Permission model."""
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin
from app.models.role import role_permissions


class Permission(Base, TimestampMixin):
    """Permission model for RBAC."""
    __tablename__ = "users_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), unique=True, nullable=False, index=True)
    description = Column(String(255))

    # Relationship back to Role (defined via Role.permissions many-to-many)
    roles = relationship('Role', secondary=role_permissions, back_populates='permissions')