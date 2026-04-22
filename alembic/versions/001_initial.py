"""Initial migration: create all tables

Revision ID: 001_initial
Revises:
Create Date: 2026-04-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users table
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(), nullable=False, server_default="default"),
        sa.Column("feishu_webhook_url", sa.Text(), nullable=True),
        sa.Column("crawl_frequency_hours", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("data_retention_days", sa.Integer(), nullable=False, server_default="365"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Products table
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("platform", sa.String(20), nullable=False),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("platform_product_id", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, default=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Price history table
    op.create_table(
        "price_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("price", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, default="CNY"),
        sa.Column("scraped_at", sa.DateTime(), nullable=False),
        sa.Column("source_site", sa.String(50), nullable=True),
        sa.Column("page_hash", sa.String(), nullable=True),
    )

    # Alerts table
    op.create_table(
        "alerts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alert_type", sa.String(20), nullable=False, server_default="price_drop"),
        sa.Column("threshold_percent", sa.Numeric(5, 2), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_notified_at", sa.DateTime(), nullable=True),
        sa.Column("last_notified_price", sa.Numeric(12, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )

    # Crawl logs table
    op.create_table(
        "crawl_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=True),
        sa.Column("platform", sa.String(20), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("price", sa.Numeric(12, 2), nullable=True),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("timestamp", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("error_message", sa.Text(), nullable=True),
    )

    # Indexes
    op.create_index("ix_products_user_platform", "products", ["user_id", "platform"])
    op.create_index("ix_products_active", "products", ["active"])
    op.create_index("ix_price_history_product_scraped", "price_history", ["product_id", "scraped_at"])
    op.create_index("ix_crawl_logs_product_timestamp", "crawl_logs", ["product_id", "timestamp"])


def downgrade() -> None:
    op.drop_index("ix_crawl_logs_product_timestamp")
    op.drop_index("ix_price_history_product_scraped")
    op.drop_index("ix_products_active")
    op.drop_index("ix_products_user_platform")
    op.drop_table("crawl_logs")
    op.drop_table("alerts")
    op.drop_table("price_history")
    op.drop_table("products")
    op.drop_table("users")
