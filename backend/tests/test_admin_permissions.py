"""Tests verifying admin.py uses fine-grained require_permission instead of require_role."""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import get_current_user
from app.database import get_db
from app.main import app


def _make_user(user_id: int, role: str):
    user = MagicMock()
    user.id = user_id
    user.username = f"user{user_id}"
    user.email = f"user{user_id}@test.com"
    user.role = role
    user.is_active = True
    user.deleted_at = None
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    return user


def _setup_mock_db():
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalar.return_value = 0
    mock_result.scalars.return_value = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    async def _override():
        yield mock_session
    app.dependency_overrides[get_db] = _override


def _override_user(user):
    async def _u():
        return user
    app.dependency_overrides[get_current_user] = _u


def _clear_overrides():
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)


@pytest.mark.anyio
async def test_list_users_requires_user_read_permission():
    """普通 user 角色没有 user:read 权限，应被拒绝。"""
    _setup_mock_db()
    _override_user(_make_user(1, "user"))
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/admin/users",
                headers={"Authorization": "Bearer fake"},
            )
        assert resp.status_code == 403
    finally:
        _clear_overrides()


@pytest.mark.anyio
async def test_list_users_admin_allowed():
    """admin 拥有 user:read 权限，应能查看用户列表。"""
    _setup_mock_db()
    _override_user(_make_user(1, "admin"))
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/admin/users",
                headers={"Authorization": "Bearer fake"},
            )
        assert resp.status_code == 200
    finally:
        _clear_overrides()


@pytest.mark.anyio
async def test_delete_user_requires_user_delete_permission():
    """super_admin 拥有 user:delete 权限。删除一个不存在的 user_id，权限通过后返回 404。"""
    _setup_mock_db()
    _override_user(_make_user(1, "super_admin"))
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.delete(
                "/admin/users/99999",
                headers={"Authorization": "Bearer fake"},
            )
        assert resp.status_code == 404
    finally:
        _clear_overrides()


@pytest.mark.anyio
async def test_delete_user_regular_user_forbidden():
    """普通 user 不能删除用户。"""
    _setup_mock_db()
    _override_user(_make_user(1, "user"))
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.delete(
                "/admin/users/99999",
                headers={"Authorization": "Bearer fake"},
            )
        assert resp.status_code == 403
    finally:
        _clear_overrides()
