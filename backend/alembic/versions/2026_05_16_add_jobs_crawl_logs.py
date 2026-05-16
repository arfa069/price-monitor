"""Add jobs_crawl_logs table for BOSS job crawl logs.

Revision ID: 2026_05_16_add_jobs_crawl_logs
Revises: 2026_05_16_rname_prod_tables
Create Date: 2026-05-16
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "2026_05_16_add_jobs_crawl_logs"
down_revision: str | None = "2026_05_16_rname_prod_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "jobs_crawl_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "search_config_id",
            sa.Integer(),
            sa.ForeignKey("jobs_search_configs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("new_jobs_count", sa.Integer(), nullable=True),
        sa.Column("total_jobs_count", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index(
        "ix_jobs_crawl_logs_config_scraped",
        "jobs_crawl_logs",
        ["search_config_id", "scraped_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_jobs_crawl_logs_config_scraped")
    op.drop_table("jobs_crawl_logs")
