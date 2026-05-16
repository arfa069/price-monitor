"""Rename match_results table to jobs_match_results.

Revision ID: 2026_05_16_rname_match_results
Revises: 2026_05_16_rname_alerts
Create Date: 2026-05-16
"""
from collections.abc import Sequence

from alembic import op

revision: str = "2026_05_16_rname_match_results"
down_revision: str | None = "2026_05_16_rname_alerts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER INDEX IF EXISTS match_results_pkey RENAME TO jobs_match_results_pkey")
    op.rename_table("match_results", "jobs_match_results")


def downgrade() -> None:
    op.rename_table("jobs_match_results", "match_results")
    op.execute("ALTER INDEX IF EXISTS jobs_match_results_pkey RENAME TO match_results_pkey")
