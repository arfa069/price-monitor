"""add product_platform_crons table

Revision ID: df4df256c713
Revises: 6e478286c034
Create Date: 2026-05-02 13:18:22.175946

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'df4df256c713'
down_revision: Union[str, None] = '6e478286c034'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "product_platform_crons",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("cron_expression", sa.String(100), nullable=True,
                  comment="5-segment crontab expression. Null means no scheduled crawl for this platform."),
        sa.Column("cron_timezone", sa.String(50), nullable=True, server_default="Asia/Shanghai"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("platform"),
    )


def downgrade() -> None:
    op.drop_table("product_platform_crons")
