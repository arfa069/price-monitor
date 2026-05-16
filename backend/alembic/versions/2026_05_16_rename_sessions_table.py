"""Rename sessions table to users_sessions.

Revision ID: 2026_05_16_rename_sessions
Revises: 2026_05_16_rename_price_history
Create Date: 2026-05-16
"""
from collections.abc import Sequence

from alembic import op

revision: str = "2026_05_16_rename_sessions"
down_revision: str | None = "2026_05_16_rename_price_history"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Rename indexes to match new table name
    op.execute("ALTER INDEX IF EXISTS sessions_pkey RENAME TO users_sessions_pkey")
    op.execute("ALTER INDEX IF EXISTS sessions_token_hash_key RENAME TO users_sessions_token_hash_key")
    op.execute("ALTER INDEX IF EXISTS ix_sessions_user_id RENAME TO ix_users_sessions_user_id")
    # Rename table
    op.rename_table("sessions", "users_sessions")


def downgrade() -> None:
    op.rename_table("users_sessions", "sessions")
    op.execute("ALTER INDEX IF EXISTS users_sessions_pkey RENAME TO sessions_pkey")
    op.execute("ALTER INDEX IF EXISTS users_sessions_token_hash_key RENAME TO sessions_token_hash_key")
    op.execute("ALTER INDEX IF EXISTS ix_users_sessions_user_id RENAME TO ix_sessions_user_id")
