"""Rename resource_permissions table to users_resources_permissions.

Revision ID: 2026_05_16_rname_resrc_perms
Revises: 2026_05_16_rname_role_perms
Create Date: 2026-05-16
"""
from collections.abc import Sequence

from alembic import op

revision: str = "2026_05_16_rname_resrc_perms"
down_revision: str | None = "2026_05_16_rname_role_perms"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER INDEX IF EXISTS resource_permissions_pkey RENAME TO users_resources_permissions_pkey")
    op.rename_table("resource_permissions", "users_resources_permissions")


def downgrade() -> None:
    op.rename_table("users_resources_permissions", "resource_permissions")
    op.execute("ALTER INDEX IF EXISTS users_resources_permissions_pkey RENAME TO resource_permissions_pkey")
