"""Rename user_audit_logs → users_audit_logs, user_resumes → jobs_resumes.

Revision ID: 2026_05_16_rname_audit_resumes
Revises: 2026_05_16_rname_perms
Create Date: 2026-05-16
"""
from collections.abc import Sequence

from alembic import op

revision: str = "2026_05_16_rname_audit_resumes"
down_revision: str | None = "2026_05_16_rname_perms"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # user_audit_logs → users_audit_logs
    op.execute("ALTER INDEX IF EXISTS user_audit_logs_pkey RENAME TO users_audit_logs_pkey")
    op.rename_table("user_audit_logs", "users_audit_logs")

    # user_resumes → jobs_resumes
    op.execute("ALTER INDEX IF EXISTS user_resumes_pkey RENAME TO jobs_resumes_pkey")
    op.rename_table("user_resumes", "jobs_resumes")


def downgrade() -> None:
    op.rename_table("jobs_resumes", "user_resumes")
    op.execute("ALTER INDEX IF EXISTS jobs_resumes_pkey RENAME TO user_resumes_pkey")
    op.rename_table("users_audit_logs", "user_audit_logs")
    op.execute("ALTER INDEX IF EXISTS users_audit_logs_pkey RENAME TO user_audit_logs_pkey")
