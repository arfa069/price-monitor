"""Rename role_permissions table to users_roles_permissions.

Revision ID: 2026_05_16_rname_role_perms
Revises: 2026_05_16_rename_roles
Create Date: 2026-05-16
"""
from collections.abc import Sequence

from alembic import op

revision: str = "2026_05_16_rname_role_perms"
down_revision: str | None = "2026_05_16_rename_roles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER INDEX IF EXISTS role_permissions_pkey RENAME TO users_roles_permissions_pkey")
    op.rename_table("role_permissions", "users_roles_permissions")


def downgrade() -> None:
    op.rename_table("users_roles_permissions", "role_permissions")
    op.execute("ALTER INDEX IF EXISTS users_roles_permissions_pkey RENAME TO role_permissions_pkey")
