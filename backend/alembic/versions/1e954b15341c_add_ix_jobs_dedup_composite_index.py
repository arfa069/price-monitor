"""Add ix_jobs_dedup composite index

Revision ID: 1e954b15341c
Revises: 6ca10dabba4e
Create Date: 2026-05-07 01:10:14.261271

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1e954b15341c'
down_revision: Union[str, None] = '6ca10dabba4e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(
        "ix_jobs_dedup",
        "jobs",
        ["search_config_id", "title", "company", "salary"],
    )


def downgrade() -> None:
    op.drop_index("ix_jobs_dedup", table_name="jobs")
