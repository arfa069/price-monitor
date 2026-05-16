"""Rename permissions table to users_permissions.

Revision ID: 2026_05_16_rname_perms
Revises: 2026_05_16_rname_login_logs
Create Date: 2026-05-16
"""
from collections.abc import Sequence

from alembic import op

revision: str = "2026_05_16_rname_perms"
down_revision: str | None = "2026_05_16_rname_login_logs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER INDEX IF EXISTS permissions_pkey RENAME TO users_permissions_pkey")
    op.execute("ALTER INDEX IF EXISTS permissions_name_key RENAME TO users_permissions_name_key")
    op.rename_table("permissions", "users_permissions")


def downgrade() -> None:
    op.rename_table("users_permissions", "permissions")
    op.execute("ALTER INDEX IF EXISTS users_permissions_pkey RENAME TO permissions_pkey")
    op.execute("ALTER INDEX IF EXISTS users_permissions_name_key RENAME TO permissions_name_key")
