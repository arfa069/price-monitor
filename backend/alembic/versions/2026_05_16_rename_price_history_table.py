"""Rename price_history table to product_price_history.

Revision ID: 2026_05_16_rename_price_history
Revises: 2026_05_14_resource_permissions
Create Date: 2026-05-16
"""
from collections.abc import Sequence

from alembic import op

revision: str = "2026_05_16_rename_price_history"
down_revision: str | None = "2026_05_14_resource_permissions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Rename index before table rename
    op.execute("ALTER INDEX ix_price_history_product_scraped RENAME TO ix_product_price_history_product_scraped")
    op.rename_table("price_history", "product_price_history")


def downgrade() -> None:
    op.rename_table("product_price_history", "price_history")
    op.execute("ALTER INDEX ix_product_price_history_product_scraped RENAME TO ix_price_history_product_scraped")
