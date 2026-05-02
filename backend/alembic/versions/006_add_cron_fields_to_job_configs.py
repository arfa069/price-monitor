"""add cron fields to job_search_configs

Revision ID: 6e478286c034
Revises: c10890a48692
Create Date: 2026-05-02 12:46:22.401024

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6e478286c034'
down_revision: Union[str, None] = '608388bac1c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "job_search_configs",
        sa.Column("cron_expression", sa.String(100), nullable=True,
                  comment="5-segment crontab expression for per-config scheduling. Null means no scheduled crawl."),
    )
    op.add_column(
        "job_search_configs",
        sa.Column("cron_timezone", sa.String(50), nullable=True, server_default="Asia/Shanghai",
                  comment="Timezone for this config's cron expression"),
    )


def downgrade() -> None:
    op.drop_column("job_search_configs", "cron_timezone")
    op.drop_column("job_search_configs", "cron_expression")
