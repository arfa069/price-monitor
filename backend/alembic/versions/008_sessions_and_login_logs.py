"""Add sessions and login history tables.

Revision ID: 008_sessions_and_login_logs
Revises: 007_add_roles_and_soft_delete
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa

revision = '008_sessions_and_login_logs'
down_revision = '007_add_roles_and_soft_delete'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sessions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('token_hash', sa.String(64), unique=True, nullable=False),
        sa.Column('device', sa.String(255)),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('last_active_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_sessions_user_id', 'sessions', ['user_id'])

    op.create_table(
        'login_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('ip_address', sa.String(45)),
        sa.Column('user_agent', sa.String(512)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_login_logs_user_id', 'login_logs', ['user_id'])


def downgrade() -> None:
    op.drop_table('login_logs')
    op.drop_table('sessions')
