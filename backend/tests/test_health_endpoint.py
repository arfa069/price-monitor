"""Tests for /health endpoint response shape (post-redaction)."""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.anyio
async def test_health_returns_only_status_field():
    """脱敏后 /health 只返回 status 字段，不再泄露 db/redis/scheduler 状态。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")

    assert resp.status_code == 200
    body = resp.json()
    assert "status" in body
    assert body["status"] in ("healthy", "unhealthy")
    # 关键脱敏断言：不能泄露内部组件状态
    assert "checks" not in body
    assert "database" not in body
    assert "redis" not in body
    assert "scheduler" not in body


@pytest.mark.anyio
async def test_health_endpoint_is_public():
    """/health 不需要认证（保持容器/K8s 健康检查兼容）。"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/health")
    # 没有 Authorization header 也应返回 200
    assert resp.status_code == 200
