"""Regression tests for /admin/audit-logs listing.

Bug history: count query used `select(func.count(UserAuditLog.id)).select_from(query.subquery())`
which produced an implicit cartesian product (anon_subq, user_audit_logs),
multiplying total by row-count. 11 rows reported as 11 * 11 = 121.
"""
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import get_current_user
from app.database import get_db
from app.main import app


def _make_admin():
    user = MagicMock()
    user.id = 1
    user.username = "admin"
    user.email = "admin@example.com"
    user.role = "super_admin"
    user.is_active = True
    user.deleted_at = None
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    return user


def _make_audit_log(log_id: int):
    log = MagicMock()
    log.id = log_id
    log.actor_user_id = 1
    log.action = "user.create"
    log.target_type = "user"
    log.target_id = 100 + log_id
    log.details = {"username": f"user{log_id}"}
    log.ip_address = "127.0.0.1"
    log.user_agent = "pytest"
    log.created_at = datetime.now(UTC)
    return log


@pytest.fixture(autouse=True)
def cleanup_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_audit_log_count_does_not_explode_via_cartesian_product():
    """Total returned must equal actual row count, not row_count^2.

    This regression locks in the fix for the implicit-cartesian-product bug:
    11 rows reported as 121.
    """
    rows = [_make_audit_log(i) for i in range(1, 12)]  # 11 rows
    actual_total = len(rows)

    captured_sql: list[str] = []

    async def fake_execute(stmt, *args, **kwargs):
        captured_sql.append(str(stmt))

        # Heuristic: count_query has a func.count column; list_query selects ORM.
        compiled_text = str(stmt).lower()
        if "count(" in compiled_text:
            res = MagicMock()
            res.scalar_one_or_none.return_value = actual_total
            return res

        scalars = MagicMock()
        scalars.all.return_value = rows
        res = MagicMock()
        res.scalars.return_value = scalars
        return res

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(side_effect=fake_execute)

    admin = _make_admin()

    async def _override_user(token=None, db=None):
        return admin

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_current_user] = _override_user
    app.dependency_overrides[get_db] = _override_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/admin/audit-logs?page=1&page_size=20")

    assert response.status_code == 200
    body = response.json()

    # Primary assertion: total equals actual row count.
    assert body["total"] == actual_total, (
        f"total={body['total']} but actual rows={actual_total}. "
        "If total = actual_total ** 2, the cartesian product bug is back."
    )
    assert body["total"] != actual_total * actual_total
    assert len(body["items"]) == actual_total

    # Structural assertion: count SQL must have a single FROM table.
    count_sqls = [s for s in captured_sql if "count(" in s.lower()]
    assert count_sqls, "count query was never executed"
    count_sql = count_sqls[0].lower()
    # Implicit cartesian product surfaces as ", user_audit_logs" after a subquery alias.
    assert ", user_audit_logs" not in count_sql, (
        f"count SQL still contains implicit cartesian join:\n{count_sql}"
    )
    # Must not wrap the base select in a subquery for counting.
    assert "anon_" not in count_sql, (
        f"count SQL wraps full select in subquery, which triggers the bug:\n{count_sql}"
    )
