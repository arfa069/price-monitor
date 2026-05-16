"""Role model."""
from sqlalchemy import Column, Integer, String, ForeignKey, Table
from sqlalchemy.orm import relationship

from app.models.base import Base, TimestampMixin


role_permissions = Table(
    'users_roles_permissions',
    Base.metadata,
    Column('role_id', Integer, ForeignKey('users_roles.id', ondelete='CASCADE'), primary_key=True),
    Column('permission_id', Integer, ForeignKey('users_permissions.id', ondelete='CASCADE'), primary_key=True),
)


class Role(Base, TimestampMixin):
    """Role model for RBAC."""
    __tablename__ = "users_roles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(20), unique=True, nullable=False, index=True)
    description = Column(String(255))

    permissions = relationship('Permission', secondary=role_permissions, back_populates='roles')