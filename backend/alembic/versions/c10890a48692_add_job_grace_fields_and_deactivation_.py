"""add job grace fields and deactivation threshold

Revision ID: c10890a48692
Revises: 005_add_job_tables
Create Date: 2026-04-29 01:00:13.488735

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c10890a48692'
down_revision: Union[str, None] = '005_add_job_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add grace period fields to Job table
    op.add_column('jobs', sa.Column('consecutive_miss_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('jobs', sa.Column('last_active_at', sa.DateTime(timezone=True), nullable=True))

    # Add deactivation_threshold to JobSearchConfig
    op.add_column('job_search_configs', sa.Column('deactivation_threshold', sa.Integer(), nullable=False, server_default='3'))


def downgrade() -> None:
    op.drop_column('job_search_configs', 'deactivation_threshold')
    op.drop_column('jobs', 'last_active_at')
    op.drop_column('jobs', 'consecutive_miss_count')