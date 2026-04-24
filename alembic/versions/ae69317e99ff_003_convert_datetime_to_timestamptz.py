"""003_convert_datetime_to_timestamptz

Convert all DateTime columns to DateTime(timezone=True) to fix asyncpg
timezone-aware datetime incompatibility with TIMESTAMP WITHOUT TIME ZONE.

Revision ID: ae69317e99ff
Revises: 002_add_alerts_index
Create Date: 2026-04-22

"""
from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = 'ae69317e99ff'
down_revision: str | None = '002_add_alerts_index'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # users table
    op.alter_column('users', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False,
               existing_server_default=sa.text('now()'))
    op.alter_column('users', 'updated_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False,
               existing_server_default=sa.text('now()'))

    # products table
    op.alter_column('products', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False,
               existing_server_default=sa.text('now()'))
    op.alter_column('products', 'updated_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False,
               existing_server_default=sa.text('now()'))

    # price_history table
    op.alter_column('price_history', 'scraped_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False)

    # alerts table
    op.alter_column('alerts', 'created_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False,
               existing_server_default=sa.text('now()'))
    op.alter_column('alerts', 'updated_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False,
               existing_server_default=sa.text('now()'))
    op.alter_column('alerts', 'last_notified_at',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=True)

    # crawl_logs table
    op.alter_column('crawl_logs', 'timestamp',
               existing_type=postgresql.TIMESTAMP(),
               type_=sa.DateTime(timezone=True),
               existing_nullable=False,
               existing_server_default=sa.text('now()'))


def downgrade() -> None:
    # users table
    op.alter_column('users', 'updated_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False,
               existing_server_default=sa.text('now()'))
    op.alter_column('users', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False,
               existing_server_default=sa.text('now()'))

    # products table
    op.alter_column('products', 'updated_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False,
               existing_server_default=sa.text('now()'))
    op.alter_column('products', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False,
               existing_server_default=sa.text('now()'))

    # price_history table
    op.alter_column('price_history', 'scraped_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False)

    # alerts table
    op.alter_column('crawl_logs', 'timestamp',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False,
               existing_server_default=sa.text('now()'))
    op.alter_column('alerts', 'last_notified_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=True)
    op.alter_column('alerts', 'updated_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False,
               existing_server_default=sa.text('now()'))
    op.alter_column('alerts', 'created_at',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False,
               existing_server_default=sa.text('now()'))

    # crawl_logs table
    op.alter_column('crawl_logs', 'timestamp',
               existing_type=sa.DateTime(timezone=True),
               type_=postgresql.TIMESTAMP(),
               existing_nullable=False,
               existing_server_default=sa.text('now()'))
