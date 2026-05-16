"""Rename product_platform_crons → products_platform_crons, product_price_history → products_price_history.

Revision ID: 2026_05_16_rname_prod_tables
Revises: 2026_05_16_rname_match_results
Create Date: 2026-05-16
"""
from collections.abc import Sequence

from alembic import op

revision: str = "2026_05_16_rname_prod_tables"
down_revision: str | None = "2026_05_16_rname_match_results"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # product_platform_crons → products_platform_crons
    op.execute("ALTER INDEX IF EXISTS product_platform_crons_pkey RENAME TO products_platform_crons_pkey")
    op.execute("ALTER INDEX IF EXISTS product_platform_crons_platform_key RENAME TO products_platform_crons_platform_key")
    op.rename_table("product_platform_crons", "products_platform_crons")

    # product_price_history → products_price_history
    op.execute("ALTER INDEX IF EXISTS price_history_pkey RENAME TO products_price_history_pkey")
    op.execute("ALTER INDEX IF EXISTS ix_product_price_history_product_scraped RENAME TO ix_products_price_history_product_scraped")
    op.rename_table("product_price_history", "products_price_history")


def downgrade() -> None:
    op.rename_table("products_price_history", "product_price_history")
    op.execute("ALTER INDEX IF EXISTS ix_products_price_history_product_scraped RENAME TO ix_product_price_history_product_scraped")
    op.execute("ALTER INDEX IF EXISTS products_price_history_pkey RENAME TO price_history_pkey")

    op.rename_table("products_platform_crons", "product_platform_crons")
    op.execute("ALTER INDEX IF EXISTS products_platform_crons_platform_key RENAME TO product_platform_crons_platform_key")
    op.execute("ALTER INDEX IF EXISTS products_platform_crons_pkey RENAME TO product_platform_crons_pkey")
