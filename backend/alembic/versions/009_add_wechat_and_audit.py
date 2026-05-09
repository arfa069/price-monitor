"""Add wechat fields and audit log table.

Revision ID: 009_add_wechat_and_audit
Revises: 008_sessions_and_login_logs
Create Date: 2026-05-09
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '009_add_wechat_and_audit'
down_revision = '008_sessions_and_login_logs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add wechat fields to users table
    op.add_column("users", sa.Column("wechat_openid", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("wechat_union_id", sa.String(64), nullable=True))
    op.add_column("users", sa.Column("wechat_bind_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_users_wechat_openid", "users", ["wechat_openid"], unique=True)

    # Create user_audit_logs table
    op.create_table(
        "user_audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("actor_user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(50), nullable=False),
        sa.Column("target_type", sa.String(50), nullable=True),
        sa.Column("target_id", sa.Integer(), nullable=True),
        sa.Column("details", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_logs_actor_user_id", "user_audit_logs", ["actor_user_id"])
    op.create_index("ix_audit_logs_created_at", "user_audit_logs", ["created_at"])
    op.create_index("ix_audit_logs_action", "user_audit_logs", ["action"])


def downgrade() -> None:
    op.drop_table("user_audit_logs")
    op.drop_index("ix_users_wechat_openid", table_name="users")
    op.drop_column("users", "wechat_bind_at")
    op.drop_column("users", "wechat_union_id")
    op.drop_column("users", "wechat_openid")
