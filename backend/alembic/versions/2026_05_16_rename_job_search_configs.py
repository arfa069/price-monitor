"""Rename job_search_configs to jobs_search_configs.

Revision ID: 2026_05_16_rname_job_configs
Revises: 2026_05_16_rname_audit_resumes
Create Date: 2026-05-16
"""
from collections.abc import Sequence

from alembic import op

revision: str = "2026_05_16_rname_job_configs"
down_revision: str | None = "2026_05_16_rname_audit_resumes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("ALTER INDEX IF EXISTS job_search_configs_pkey RENAME TO jobs_search_configs_pkey")
    op.rename_table("job_search_configs", "jobs_search_configs")


def downgrade() -> None:
    op.rename_table("jobs_search_configs", "job_search_configs")
    op.execute("ALTER INDEX IF EXISTS jobs_search_configs_pkey RENAME TO job_search_configs_pkey")
