"""
User Management Real Database Integration Tests
Uses real PostgreSQL DB to verify CRUD operations persist correctly.

Run manually with: pytest tests/test_user_management_realdb.py -v
Requires: running DB with admin user (username=admin, password=adminpassword)
"""
import pytest
import uuid
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.database import AsyncSessionLocal
from app.main import app
from app.models.user import User


async def run_in_session(fn):
    async with AsyncSessionLocal() as session:
        try:
            return await fn(session)
        except Exception:
            await session.rollback()
            raise


async def get_admin_token():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/auth/login", json={
            "username": "admin",
            "password": "adminpassword"
        })
        return response.json()["access_token"]


@pytest.mark.skip(reason="real DB test - requires PostgreSQL + admin user seeded")
class TestUserManagementRealDb:
    @pytest.mark.asyncio
    async def test_create_user_persists_to_db(self):
        test_username = f"testuser_{uuid.uuid4().hex[:8]}"
        test_email = f"{test_username}@example.com"
        admin_token = await get_admin_token()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/admin/users",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "username": test_username,
                    "email": test_email,
                    "password": "password123",
                    "role": "user"
                }
            )

        assert response.status_code == 201
        user_id = response.json()["id"]

        async def _verify(session):
            result = await session.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()

        db_user = await run_in_session(_verify)
        assert db_user is not None
        assert db_user.username == test_username
        assert db_user.deleted_at is None

        async def _cleanup(session):
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()

        await run_in_session(_cleanup)

    @pytest.mark.asyncio
    async def test_soft_delete_sets_deleted_at(self):
        test_username = f"testuser_{uuid.uuid4().hex[:8]}"
        test_email = f"{test_username}@example.com"
        admin_token = await get_admin_token()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create_resp = await client.post(
                "/admin/users",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "username": test_username,
                    "email": test_email,
                    "password": "password123",
                    "role": "user"
                }
            )
            user_id = create_resp.json()["id"]

            delete_resp = await client.delete(
                f"/admin/users/{user_id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )

        assert delete_resp.status_code == 200

        async def _verify(session):
            result = await session.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()

        db_user = await run_in_session(_verify)
        assert db_user is not None
        assert db_user.deleted_at is not None

    @pytest.mark.asyncio
    async def test_restore_user_clears_deleted_at(self):
        test_username = f"testuser_{uuid.uuid4().hex[:8]}"
        test_email = f"{test_username}@example.com"
        admin_token = await get_admin_token()

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            create_resp = await client.post(
                "/admin/users",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={
                    "username": test_username,
                    "email": test_email,
                    "password": "password123",
                    "role": "user"
                }
            )
            user_id = create_resp.json()["id"]

            await client.delete(
                f"/admin/users/{user_id}",
                headers={"Authorization": f"Bearer {admin_token}"}
            )

            restore_resp = await client.patch(
                f"/admin/users/{user_id}",
                headers={"Authorization": f"Bearer {admin_token}"},
                json={"is_active": True}
            )

        assert restore_resp.status_code == 200

        async def _verify(session):
            result = await session.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()

        db_user = await run_in_session(_verify)
        assert db_user is not None
        assert db_user.deleted_at is None

        async def _cleanup(session):
            await session.execute(delete(User).where(User.id == user_id))
            await session.commit()

        await run_in_session(_cleanup)
