"""Merge branches

Revision ID: 6ca10dabba4e
Revises: 2026_05_03_add_job_match, 6090a1b2c3d4
Create Date: 2026-05-07 01:10:08.567975

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6ca10dabba4e'
down_revision: Union[str, None] = ('2026_05_03_add_job_match', '6090a1b2c3d4')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
