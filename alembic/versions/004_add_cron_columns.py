"""Add crawl_cron and crawl_timezone columns to users table.

Revision ID: 004_add_cron_columns
Revises: ae69317e99ff
Create Date: 2026-04-23
"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "004_add_cron_columns"
down_revision = "ae69317e99ff"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("crawl_cron", sa.String(), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column("crawl_timezone", sa.String(), nullable=True, server_default="Asia/Shanghai"),
    )


def downgrade() -> None:
    op.drop_column("users", "crawl_timezone")
    op.drop_column("users", "crawl_cron")
