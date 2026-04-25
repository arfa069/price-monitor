"""add job tables: job_search_configs and jobs

Revision ID: 005_add_job_tables
Revises: 004_add_cron_columns
Create Date: 2026-04-26

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "005_add_job_tables"
down_revision = "004_add_cron_columns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # job_search_configs 表
    op.create_table(
        "job_search_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("keyword", sa.String(length=200), nullable=True),
        sa.Column("city_code", sa.String(length=20), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("experience", sa.String(length=50), nullable=True),
        sa.Column("education", sa.String(length=50), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notify_on_new", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # jobs 表
    op.create_table(
        "jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_id", sa.String(length=100), nullable=False),
        sa.Column("search_config_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=300), nullable=True),
        sa.Column("company", sa.String(length=200), nullable=True),
        sa.Column("company_id", sa.String(length=100), nullable=True),
        sa.Column("salary", sa.String(length=100), nullable=True),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("location", sa.String(length=200), nullable=True),
        sa.Column("experience", sa.String(length=100), nullable=True),
        sa.Column("education", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.ForeignKeyConstraint(
            ["search_config_id"], ["job_search_configs.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id"),
    )
    op.create_index("ix_jobs_job_id", "jobs", ["job_id"])
    op.create_index("ix_jobs_search_config_id", "jobs", ["search_config_id"])

    # User 表新增 job_crawl_cron 列
    op.add_column(
        "users", sa.Column("job_crawl_cron", sa.String(length=100), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("users", "job_crawl_cron")
    op.drop_index("ix_jobs_search_config_id", table_name="jobs")
    op.drop_index("ix_jobs_job_id", table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("job_search_configs")
