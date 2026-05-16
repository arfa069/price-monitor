"""Rename alerts table to products_alerts.

Revision ID: 2026_05_16_rname_alerts
Revises: 2026_05_16_rname_job_configs
Create Date: 2026-05-16
"""
from collections.abc import Sequence

from alembic import op

revision: str = "2026_05_16_rname_alerts"
down_revision: str | None = "2026_05_16_rname_job_configs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER INDEX IF EXISTS alerts_pkey RENAME TO products_alerts_pkey")
    op.rename_table("alerts", "products_alerts")


def downgrade() -> None:
    op.rename_table("products_alerts", "alerts")
    op.execute("ALTER INDEX IF EXISTS products_alerts_pkey RENAME TO alerts_pkey")
