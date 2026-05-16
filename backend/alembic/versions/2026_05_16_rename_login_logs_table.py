"""Rename login_logs table to users_login_logs.

Revision ID: 2026_05_16_rname_login_logs
Revises: 2026_05_16_rname_resrc_perms
Create Date: 2026-05-16
"""
from collections.abc import Sequence

from alembic import op

revision: str = "2026_05_16_rname_login_logs"
down_revision: str | None = "2026_05_16_rname_resrc_perms"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER INDEX IF EXISTS login_logs_pkey RENAME TO users_login_logs_pkey")
    op.execute("ALTER INDEX IF EXISTS ix_login_logs_user_id RENAME TO ix_users_login_logs_user_id")
    op.rename_table("login_logs", "users_login_logs")


def downgrade() -> None:
    op.rename_table("users_login_logs", "login_logs")
    op.execute("ALTER INDEX IF EXISTS users_login_logs_pkey RENAME TO login_logs_pkey")
    op.execute("ALTER INDEX IF EXISTS ix_users_login_logs_user_id RENAME TO ix_login_logs_user_id")
