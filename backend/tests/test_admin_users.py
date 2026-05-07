"""Integration tests for admin user management API (Task 4).

TDD approach: tests define expected behavior, then implementation is written.
"""
from unittest.mock import AsyncMock, MagicMock
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.security import get_password_hash, get_current_user
from app.database import get_db
from app.main import app
from app.models.user import User


# --- Fixtures ---


@pytest.fixture
def mock_db_session():
    """Mock database session for admin tests."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


def create_mock_user(user_id, username, email, role, is_active=True, deleted_at=None):
    """Create a mock user with minimal attributes (no SQLAlchemy relationships)."""
    user = MagicMock()
    user.id = user_id
    user.username = username
    user.email = email
    user.role = role
    user.is_active = is_active
    user.deleted_at = deleted_at
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    # Avoid SQLAlchemy relationship loading by not using spec=User
    return user


@pytest.fixture
def mock_get_db(mock_db_session):
    """Override get_db dependency with mock session."""
    async def _override():
        yield mock_db_session
    app.dependency_overrides[get_db] = _override
    yield mock_db_session
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def admin_user():
    """Admin user fixture."""
    return create_mock_user(1, "admin", "admin@example.com", "admin")


@pytest.fixture
def regular_user():
    """Regular user fixture."""
    return create_mock_user(2, "regular", "regular@example.com", "user")


def setup_admin_mock(admin_user):
    """Set up mock get_current_user to return admin user."""
    async def mock_get_current_user(token=None, db=None):
        return admin_user
    app.dependency_overrides[get_current_user] = mock_get_current_user


def setup_non_admin_mock():
    """Set up mock get_current_user to raise 403."""
    async def mock_get_current_user(token=None, db=None):
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    app.dependency_overrides[get_current_user] = mock_get_current_user


def clear_auth_mocks():
    """Remove auth mocks."""
    app.dependency_overrides.pop(get_current_user, None)


# --- GET /admin/users Tests ---


@pytest.mark.asyncio
async def test_admin_list_users_returns_200(admin_user, mock_get_db):
    """GET /admin/users returns paginated user list for admin."""
    setup_admin_mock(admin_user)

    try:
        user1 = create_mock_user(1, "admin", "admin@example.com", "admin")
        user2 = create_mock_user(2, "user2", "user2@example.com", "user")

        # Mock count query
        mock_count_result = MagicMock()
        mock_count_result.scalar_one_or_none.return_value = 2

        # Mock list query
        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value.all.return_value = [user1, user2]

        mock_get_db.execute.side_effect = [mock_count_result, mock_list_result]

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/admin/users")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["page"] == 1
        assert data["page_size"] == 20
        assert len(data["items"]) == 2
    finally:
        clear_auth_mocks()


@pytest.mark.asyncio
async def test_admin_list_users_with_search(admin_user, mock_get_db):
    """GET /admin/users?search=term filters by username/email."""
    setup_admin_mock(admin_user)

    try:
        user = create_mock_user(1, "searched", "searched@example.com", "user")

        mock_count_result = MagicMock()
        mock_count_result.scalar_one_or_none.return_value = 1

        mock_list_result = MagicMock()
        mock_list_result.scalars.return_value.all.return_value = [user]

        mock_get_db.execute.side_effect = [mock_count_result, mock_list_result]

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/admin/users?search=searched")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
    finally:
        clear_auth_mocks()


@pytest.mark.asyncio
async def test_non_admin_gets_403_on_list(mock_get_db):
    """GET /admin/users returns 403 for non-admin user."""
    setup_non_admin_mock()

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/admin/users")

        assert response.status_code == 403
    finally:
        clear_auth_mocks()


@pytest.mark.asyncio
async def test_unauthenticated_gets_401_on_list(mock_get_db):
    """GET /admin/users returns 401 for unauthenticated user."""
    clear_auth_mocks()
    # Don't set up any auth override - let it try real auth which will fail

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/admin/users")

    assert response.status_code == 401


# --- POST /admin/users Tests ---


@pytest.mark.asyncio
async def test_admin_create_user_returns_201(admin_user, mock_get_db):
    """POST /admin/users creates user and returns 201."""
    setup_admin_mock(admin_user)

    try:
        # Mock no existing user
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_get_db.execute.return_value = mock_result

        def mock_refresh(user):
            user.id = 3
            user.created_at = datetime.now(UTC)
        mock_get_db.refresh.side_effect = mock_refresh

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/admin/users",
                json={
                    "username": "newuser",
                    "email": "new@example.com",
                    "password": "newpass123",
                    "role": "user",
                },
            )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"
        assert data["role"] == "user"
        assert data["is_active"] is True
    finally:
        clear_auth_mocks()


@pytest.mark.asyncio
async def test_create_duplicate_username_returns_400(admin_user, mock_get_db):
    """POST /admin/users with duplicate username returns 400."""
    setup_admin_mock(admin_user)

    try:
        # Mock existing user found
        existing = create_mock_user(99, "existinguser", "existing@example.com", "user")

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        mock_get_db.execute.return_value = mock_result

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/admin/users",
                json={
                    "username": "existinguser",
                    "email": "new@example.com",
                    "password": "newpass123",
                },
            )

        assert response.status_code == 400
    finally:
        clear_auth_mocks()


# --- GET /admin/users/{user_id} Tests ---


@pytest.mark.asyncio
async def test_admin_get_user_returns_200(admin_user, regular_user, mock_get_db):
    """GET /admin/users/{user_id} returns user for admin."""
    setup_admin_mock(admin_user)

    try:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = regular_user
        mock_get_db.execute.return_value = mock_result

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/admin/users/2")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 2
        assert data["username"] == "regular"
    finally:
        clear_auth_mocks()


@pytest.mark.asyncio
async def test_get_nonexistent_user_returns_404(admin_user, mock_get_db):
    """GET /admin/users/{user_id} returns 404 for non-existent user."""
    setup_admin_mock(admin_user)

    try:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_get_db.execute.return_value = mock_result

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/admin/users/999")

        assert response.status_code == 404
    finally:
        clear_auth_mocks()


# --- PATCH /admin/users/{user_id} Tests ---


@pytest.mark.asyncio
async def test_admin_update_user_returns_200(admin_user, regular_user, mock_get_db):
    """PATCH /admin/users/{user_id} updates user and returns 200."""
    setup_admin_mock(admin_user)

    try:
        # First call: find user, Second call: check username conflict
        mock_result1 = MagicMock()
        mock_result1.scalar_one_or_none.return_value = regular_user

        mock_result2 = MagicMock()
        mock_result2.scalar_one_or_none.return_value = None  # No conflict

        mock_get_db.execute.side_effect = [mock_result1, mock_result2]

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/admin/users/2",
                json={"username": "updateduser"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["username"] == "updateduser"
    finally:
        clear_auth_mocks()


@pytest.mark.asyncio
async def test_admin_soft_delete_user_via_patch_returns_200(admin_user, regular_user, mock_get_db):
    """PATCH /admin/users/{user_id} with is_active=False soft deletes user."""
    setup_admin_mock(admin_user)

    try:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = regular_user
        mock_get_db.execute.return_value = mock_result

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/admin/users/2",
                json={"is_active": False},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is False
    finally:
        clear_auth_mocks()


@pytest.mark.asyncio
async def test_admin_restore_user_via_patch_returns_200(admin_user, mock_get_db):
    """PATCH /admin/users/{user_id} with is_active=True restores soft-deleted user."""
    setup_admin_mock(admin_user)

    try:
        # Soft-deleted user
        deleted_user = create_mock_user(2, "deleteduser", "deleted@example.com", "user", is_active=False, deleted_at=datetime.now(UTC))

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = deleted_user
        mock_get_db.execute.return_value = mock_result

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/admin/users/2",
                json={"is_active": True},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True
    finally:
        clear_auth_mocks()


# --- DELETE /admin/users/{user_id} Tests ---


@pytest.mark.asyncio
async def test_admin_delete_user_returns_200(admin_user, regular_user, mock_get_db):
    """DELETE /admin/users/{user_id} soft deletes user and cleans up sessions."""
    setup_admin_mock(admin_user)

    try:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = regular_user
        mock_get_db.execute.return_value = mock_result

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/admin/users/2")

        assert response.status_code == 200
    finally:
        clear_auth_mocks()


@pytest.mark.asyncio
async def test_admin_delete_self_returns_400(admin_user, mock_get_db):
    """DELETE /admin/users/{user_id} returns 400 when admin tries to delete themselves."""
    setup_admin_mock(admin_user)

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/admin/users/1")  # admin_user.id == 1

        assert response.status_code == 400
    finally:
        clear_auth_mocks()


@pytest.mark.asyncio
async def test_delete_nonexistent_user_returns_404(admin_user, mock_get_db):
    """DELETE /admin/users/{user_id} returns 404 for non-existent user."""
    setup_admin_mock(admin_user)

    try:
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_get_db.execute.return_value = mock_result

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/admin/users/999")

        assert response.status_code == 404
    finally:
        clear_auth_mocks()


# --- Non-admin access tests ---


@pytest.mark.asyncio
async def test_non_admin_gets_403_on_create(mock_get_db):
    """POST /admin/users returns 403 for non-admin user."""
    setup_non_admin_mock()

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/admin/users",
                json={
                    "username": "hacker",
                    "email": "hacker@evil.com",
                    "password": "hax",
                },
            )

        assert response.status_code == 403
    finally:
        clear_auth_mocks()


@pytest.mark.asyncio
async def test_non_admin_gets_403_on_get_single(mock_get_db):
    """GET /admin/users/{user_id} returns 403 for non-admin user."""
    setup_non_admin_mock()

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/admin/users/1")

        assert response.status_code == 403
    finally:
        clear_auth_mocks()


@pytest.mark.asyncio
async def test_non_admin_gets_403_on_update(mock_get_db):
    """PATCH /admin/users/{user_id} returns 403 for non-admin user."""
    setup_non_admin_mock()

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.patch(
                "/admin/users/1",
                json={"username": "hacked"},
            )

        assert response.status_code == 403
    finally:
        clear_auth_mocks()


@pytest.mark.asyncio
async def test_non_admin_gets_403_on_delete(mock_get_db):
    """DELETE /admin/users/{user_id} returns 403 for non-admin user."""
    setup_non_admin_mock()

    try:
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.delete("/admin/users/1")

        assert response.status_code == 403
    finally:
        clear_auth_mocks()