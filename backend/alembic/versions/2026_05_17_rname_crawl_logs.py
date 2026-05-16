"""Rename crawl_logs -> products_crawl_logs.

Revision ID: 2026_05_17_rname_crawl_logs
Revises: 2026_05_16_add_jobs_crawl_logs
Create Date: 2026-05-17
"""

from typing import ClassVar

from alembic import op
import sqlalchemy as sa

revision: str = "2026_05_17_rname_crawl_logs"
down_revision: str | None = "2026_05_16_add_jobs_crawl_logs"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.rename_table("crawl_logs", "products_crawl_logs")
    op.execute("ALTER INDEX ix_crawl_logs_product_timestamp RENAME TO ix_products_crawl_logs_product_timestamp")


def downgrade() -> None:
    op.execute("ALTER INDEX ix_products_crawl_logs_product_timestamp RENAME TO ix_crawl_logs_product_timestamp")
    op.rename_table("products_crawl_logs", "crawl_logs")
