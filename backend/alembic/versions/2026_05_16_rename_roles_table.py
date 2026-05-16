"""Rename roles table to users_roles.

Revision ID: 2026_05_16_rename_roles
Revises: 2026_05_16_rename_sessions
Create Date: 2026-05-16
"""
from collections.abc import Sequence

from alembic import op

revision: str = "2026_05_16_rename_roles"
down_revision: str | None = "2026_05_16_rename_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Rename indexes to match new table name
    op.execute("ALTER INDEX IF EXISTS roles_pkey RENAME TO users_roles_pkey")
    op.execute("ALTER INDEX IF EXISTS roles_name_key RENAME TO users_roles_name_key")
    # Rename table
    op.rename_table("roles", "users_roles")


def downgrade() -> None:
    op.rename_table("users_roles", "roles")
    op.execute("ALTER INDEX IF EXISTS users_roles_pkey RENAME TO roles_pkey")
    op.execute("ALTER INDEX IF EXISTS users_roles_name_key RENAME TO roles_name_key")
