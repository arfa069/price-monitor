"""Add roles and soft delete to users.

Revision ID: 007_add_roles_and_soft_delete
Revises: 1e954b15341c
Create Date: 2026-05-07
"""
from alembic import op
import sqlalchemy as sa

revision = '007_add_roles_and_soft_delete'
down_revision = '1e954b15341c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 新增 role 列，默认 'user'
    op.add_column('users', sa.Column('role', sa.String(20), nullable=False, server_default='user'))

    # 新增 deleted_at 列，软删除时间戳
    op.add_column('users', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))

    # 创建权限表
    op.create_table(
        'permissions',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(50), unique=True, nullable=False),
        sa.Column('description', sa.String(255)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 创建角色表
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(20), unique=True, nullable=False),
        sa.Column('description', sa.String(255)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 创建角色-权限关联表
    op.create_table(
        'role_permissions',
        sa.Column('role_id', sa.Integer(), sa.ForeignKey('roles.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('permission_id', sa.Integer(), sa.ForeignKey('permissions.id', ondelete='CASCADE'), primary_key=True),
    )

    # 插入初始角色数据
    op.execute("""
        INSERT INTO roles (name, description) VALUES
        ('user', '普通用户'),
        ('admin', '运营管理员'),
        ('super_admin', '系统管理员')
    """)

    # 插入初始权限数据
    op.execute("""
        INSERT INTO permissions (name, description) VALUES
        ('users:read', '查看用户列表'),
        ('users:write', '创建/编辑用户'),
        ('users:delete', '删除用户'),
        ('profile:write', '修改个人资料'),
        ('profile:password', '修改个人密码')
    """)

    # 绑定权限到角色 (user 只有 profile 权限)
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT 1, 4 UNION ALL  -- user -> profile:write
        SELECT 1, 5            -- user -> profile:password
    """)

    # admin 有全部权限
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT 2, 1 UNION ALL  -- admin -> users:read
        SELECT 2, 2 UNION ALL  -- admin -> users:write
        SELECT 2, 3 UNION ALL  -- admin -> users:delete
        SELECT 2, 4 UNION ALL  -- admin -> profile:write
        SELECT 2, 5            -- admin -> profile:password
    """)

    # super_admin 有全部权限
    op.execute("""
        INSERT INTO role_permissions (role_id, permission_id)
        SELECT 3, 1 UNION ALL
        SELECT 3, 2 UNION ALL
        SELECT 3, 3 UNION ALL
        SELECT 3, 4 UNION ALL
        SELECT 3, 5
    """)


def downgrade() -> None:
    op.drop_table('role_permissions')
    op.drop_table('roles')
    op.drop_table('permissions')
    op.drop_column('users', 'deleted_at')
    op.drop_column('users', 'role')
