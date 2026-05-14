"""Resource-level permission model for per-resource ACL grants."""
from sqlalchemy import Column, ForeignKey, Index, Integer, String, UniqueConstraint

from app.models.base import Base, TimestampMixin


class ResourcePermission(Base, TimestampMixin):
    """Per-resource permission grant.

    Each row means a subject can perform a permission on one resource.
    The table is grant-only; deny/override semantics are intentionally absent.
    """

    __tablename__ = "resource_permissions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    subject_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    subject_type = Column(String(20), nullable=False, default="user")
    resource_type = Column(String(20), nullable=False)
    resource_id = Column(String(255), nullable=False)
    permission = Column(String(20), nullable=False)
    granted_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "subject_id",
            "subject_type",
            "resource_type",
            "resource_id",
            "permission",
            name="uq_resource_permission_key",
        ),
        Index(
            "idx_rp_subject_lookup",
            "subject_id",
            "subject_type",
            "resource_type",
            "permission",
        ),
    )
