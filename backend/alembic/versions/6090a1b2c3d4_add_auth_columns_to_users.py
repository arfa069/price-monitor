"""add auth columns to users

Revision ID: 6090a1b2c3d4
Revises: a44585027bb2
Create Date: 2026-05-06 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6090a1b2c3d4'
down_revision: Union[str, None] = 'a44585027bb2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new auth columns
    op.add_column("users", sa.Column("email", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("hashed_password", sa.String(255), nullable=True))
    op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"))
    
    # Create unique indexes for username and email
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    
    # Set default values for existing users (user with id=1)
    op.execute("UPDATE users SET email = 'default@localhost' WHERE id = 1")
    op.execute("UPDATE users SET hashed_password = '' WHERE id = 1")


def downgrade() -> None:
    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "is_active")
    op.drop_column("users", "hashed_password")
    op.drop_column("users", "email")
