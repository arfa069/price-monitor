"""Add alerts index and rename type column to alert_type

Revision ID: 002_add_alerts_index
Revises: 001_initial
Create Date: 2026-04-22

"""
from typing import Sequence, Union

from alembic import op


revision: str = "002_add_alerts_index"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add composite index on (product_id, active) for efficient alert queries
    op.create_index(
        "ix_alerts_product_active",
        "alerts",
        ["product_id", "active"],
    )

    # Add single-column index on active for filtering active alerts
    op.create_index(
        "ix_alerts_active",
        "alerts",
        ["active"],
    )


def downgrade() -> None:
    op.drop_index("ix_alerts_active")
    op.drop_index("ix_alerts_product_active")
