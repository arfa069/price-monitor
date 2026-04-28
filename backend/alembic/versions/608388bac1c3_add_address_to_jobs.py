"""add address to jobs

Revision ID: 608388bac1c3
Revises: c10890a48692
Create Date: 2026-04-29 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '608388bac1c3'
down_revision: Union[str, None] = 'c10890a48692'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('jobs', sa.Column('address', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('jobs', 'address')
