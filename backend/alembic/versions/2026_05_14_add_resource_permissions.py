"""Add resource permissions table.

Revision ID: 2026_05_14_resource_permissions
Revises: 009_add_wechat_and_audit
Create Date: 2026-05-14
"""
import sqlalchemy as sa

from alembic import op

revision = "2026_05_14_resource_permissions"
down_revision = "009_add_wechat_and_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "resource_permissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("subject_id", sa.Integer(), nullable=False),
        sa.Column("subject_type", sa.String(length=20), nullable=False),
        sa.Column("resource_type", sa.String(length=20), nullable=False),
        sa.Column("resource_id", sa.String(length=255), nullable=False),
        sa.Column("permission", sa.String(length=20), nullable=False),
        sa.Column("granted_by", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["subject_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["granted_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "subject_id",
            "subject_type",
            "resource_type",
            "resource_id",
            "permission",
            name="uq_resource_permission_key",
        ),
    )
    op.create_index(
        "idx_rp_subject_lookup",
        "resource_permissions",
        ["subject_id", "subject_type", "resource_type", "permission"],
    )


def downgrade() -> None:
    op.drop_index("idx_rp_subject_lookup", table_name="resource_permissions")
    op.drop_table("resource_permissions")
