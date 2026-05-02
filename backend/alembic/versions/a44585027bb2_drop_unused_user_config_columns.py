"""drop unused user config columns

Revision ID: a44585027bb2
Revises: df4df256c713
Create Date: 2026-05-02 14:24:58.529051

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a44585027bb2'
down_revision: Union[str, None] = 'df4df256c713'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("users", "crawl_frequency_hours")
    op.drop_column("users", "crawl_cron")
    op.drop_column("users", "crawl_timezone")
    op.drop_column("users", "job_crawl_cron")


def downgrade() -> None:
    op.add_column("users", sa.Column("crawl_frequency_hours", sa.SmallInteger(), nullable=False, server_default="1"))
    op.add_column("users", sa.Column("crawl_cron", sa.String(), nullable=True))
    op.add_column("users", sa.Column("crawl_timezone", sa.String(), nullable=True, server_default="Asia/Shanghai"))
    op.add_column("users", sa.Column("job_crawl_cron", sa.String(), nullable=True))
