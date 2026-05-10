"""Tests for /scheduler/status admin-only access control."""
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import get_current_user
from app.main import app


def _make_user(role: str):
    user = MagicMock()
    user.id = 1
    user.username = "tester"
    user.email = "tester@test.com"
    user.role = role
    user.is_active = True
    user.deleted_at = None
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    return user


@pytest.mark.anyio
async def test_scheduler_status_unauthenticated_returns_401():
    """匿名访问 /scheduler/status 应被拒绝（之前是任何人都能看）。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/scheduler/status")
    assert resp.status_code in (401, 403)


@pytest.mark.anyio
async def test_scheduler_status_regular_user_forbidden():
    """普通 user 角色不应能查看调度状态。"""
    async def fake_user():
        return _make_user("user")
    app.dependency_overrides[get_current_user] = fake_user
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/scheduler/status",
                headers={"Authorization": "Bearer fake"},
            )
        assert resp.status_code == 403
    finally:
        app.dependency_overrides.pop(get_current_user, None)


@pytest.mark.anyio
async def test_scheduler_status_admin_allowed():
    """admin 可以查看调度状态。"""
    async def fake_user():
        return _make_user("admin")
    app.dependency_overrides[get_current_user] = fake_user
    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.get(
                "/scheduler/status",
                headers={"Authorization": "Bearer fake"},
            )
        # 无论 scheduler 是 running 还是 not_started，admin 都能拿到响应
        assert resp.status_code in (200, 503)
    finally:
        app.dependency_overrides.pop(get_current_user, None)
