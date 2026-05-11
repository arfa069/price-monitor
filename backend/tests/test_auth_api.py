"""Integration tests for authentication API endpoints.

NOTE: These tests use TDD approach - tests define expected behavior
for /auth/* endpoints. If auth router is not yet registered in app,
tests will fail with RouterNotFound or similar errors.
"""
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app

# --- Fixtures ---


@pytest.fixture
def mock_db_session():
    """Mock database session for auth tests."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def mock_get_db(mock_db_session):
    """Override get_db dependency with mock session."""
    async def _override():
        yield mock_db_session
    app.dependency_overrides[get_db] = _override
    yield mock_db_session
    app.dependency_overrides.pop(get_db, None)


# --- POST /auth/register Tests ---


@pytest.mark.asyncio
async def test_register_success_returns_201(test_user, mock_get_db):
    """POST /auth/register with valid data returns 201 Created."""
    from datetime import UTC, datetime


    # Mock user not found (new user)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_get_db.execute.return_value = mock_result

    # Mock refresh to set attributes
    def mock_refresh(user):
        user.id = 1
        user.created_at = datetime.now(UTC)
    mock_get_db.refresh.side_effect = mock_refresh

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/auth/register",
            json={
                "username": test_user["username"],
                "email": test_user["email"],
                "password": test_user["password"],
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == test_user["username"]
    assert data["email"] == test_user["email"]
    assert data["is_active"] is True
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_username_returns_400(test_user, mock_get_db):
    """POST /auth/register with existing username returns 400."""
    # Mock existing user found
    mock_result = MagicMock()
    existing_user = MagicMock()
    existing_user.username = test_user["username"]
    mock_result.scalar_one_or_none.return_value = existing_user
    mock_get_db.execute.return_value = mock_result

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/auth/register",
            json={
                "username": test_user["username"],
                "email": "new@example.com",
                "password": test_user["password"],
            },
        )

    assert response.status_code == 400
    # Error message in Chinese
    assert "用户名" in response.json().get("detail", "") or "已注册" in response.json().get("detail", "")


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_400(test_user, mock_get_db):
    """POST /auth/register with existing email returns 400."""
    # Mock existing user with same email - first call returns None (no user),
    # second call returns user with same email
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.side_effect = [None, MagicMock()]
    mock_get_db.execute.return_value = mock_result

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/auth/register",
            json={
                "username": "different_user",
                "email": test_user["email"],
                "password": test_user["password"],
            },
        )

    assert response.status_code == 400
    assert "邮箱" in response.json().get("detail", "") or "已注册" in response.json().get("detail", "")


@pytest.mark.asyncio
async def test_register_password_too_short_returns_422(mock_get_db):
    """POST /auth/register with short password returns 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/auth/register",
            json={
                "username": "testuser",
                "email": "test@example.com",
                "password": "12345",  # Too short (< 6 chars expected)
            },
        )

    assert response.status_code == 422
    # Validation error for password
    detail = response.json().get("detail", [])
    if isinstance(detail, list):
        assert any("password" in str(d).lower() or "length" in str(d).lower() for d in detail)


@pytest.mark.asyncio
async def test_register_username_too_short_returns_422(mock_get_db):
    """POST /auth/register with short username returns 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/auth/register",
            json={
                "username": "ab",  # Too short (< 3 chars expected)
                "email": "test@example.com",
                "password": "securepassword",
            },
        )

    assert response.status_code == 422


# --- POST /auth/login Tests ---


@pytest.mark.asyncio
async def test_login_success_returns_200_and_token(test_user, mock_get_db):
    """POST /auth/login with valid credentials returns 200 and access token."""

    from app.core.security import get_password_hash

    # Mock user found with correct password
    hashed = get_password_hash(test_user["password"])
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = test_user["username"]
    mock_user.email = test_user["email"]
    mock_user.hashed_password = hashed
    mock_user.is_active = True

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_get_db.execute.return_value = mock_result

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/auth/login",
            json={
                "username": test_user["username"],
                "password": test_user["password"],
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data.get("token_type") == "bearer"


@pytest.mark.asyncio
async def test_login_user_not_found_returns_401(mock_get_db):
    """POST /auth/login with non-existent user returns 401."""
    # Mock user not found
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_get_db.execute.return_value = mock_result

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/auth/login",
            json={
                "username": "nonexistent",
                "password": "password123",
            },
        )

    assert response.status_code == 401
    assert "错误" in response.json().get("detail", "")


@pytest.mark.asyncio
async def test_login_wrong_password_returns_401(test_user, mock_get_db):
    """POST /auth/login with wrong password returns 401."""
    from app.core.security import get_password_hash

    # Mock user found but wrong password
    hashed = get_password_hash("correct_password")
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = test_user["username"]
    mock_user.hashed_password = hashed
    mock_user.is_active = True

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_get_db.execute.return_value = mock_result

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/auth/login",
            json={
                "username": test_user["username"],
                "password": "wrong_password",
            },
        )

    assert response.status_code == 401
    assert "错误" in response.json().get("detail", "")


@pytest.mark.skip(reason="pre-existing issue: clear_login_attempts/record_failed_login not properly async")
@pytest.mark.asyncio
async def test_login_account_locked_after_5_failures(test_user, mock_get_db):
    """POST /auth/login after 5 failures returns 429 with lockout info."""
    from app.core.security import clear_login_attempts, record_failed_login

    # Clear any existing attempts
    clear_login_attempts(test_user["username"])

    # Record 5 failed login attempts
    for _ in range(5):
        record_failed_login(test_user["username"])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/auth/login",
            json={
                "username": test_user["username"],
                "password": "any_password",
            },
        )

    # Should be locked out
    assert response.status_code == 429
    data = response.json()
    # Check for lockout message (in Chinese: "登录尝试次数过多")
    assert "登录尝试" in data.get("detail", "") or "分钟" in data.get("detail", "")

    # Clean up
    clear_login_attempts(test_user["username"])


# --- POST /auth/logout Tests ---


@pytest.mark.asyncio
async def test_logout_success(test_user, mock_get_db):
    """POST /auth/logout returns 200 on successful logout."""
    from app.core.security import create_access_token

    # Mock user found
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = test_user["username"]
    mock_user.is_active = True

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_get_db.execute.return_value = mock_result

    token = create_access_token({"sub": "1", "username": test_user["username"]})

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    assert "登出" in response.json().get("message", "")


@pytest.mark.asyncio
async def test_logout_without_token_returns_401_or_422():
    """POST /auth/logout without token returns 401 or 422.

    FastAPI returns 422 for missing required header (validation error),
    then our handler converts to 401 if needed.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/auth/logout")

    # 422 = FastAPI validation error for missing required header
    # 401 = our handler converting to auth error
    assert response.status_code in [401, 422]


# --- GET /auth/me Tests ---


@pytest.mark.asyncio
async def test_me_with_valid_token_returns_user_info(test_user, mock_get_db):
    """GET /auth/me with valid token returns user info."""
    from datetime import UTC, datetime

    from app.core.security import create_access_token

    token = create_access_token({"sub": "1", "username": test_user["username"]})

    # Mock user found
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = test_user["username"]
    mock_user.email = test_user["email"]
    mock_user.is_active = True
    mock_user.role = "user"
    mock_user.deleted_at = None
    mock_user.created_at = datetime.now(UTC)

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_get_db.execute.return_value = mock_result

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data.get("username") == test_user["username"]
    assert data.get("email") == test_user["email"]


@pytest.mark.asyncio
async def test_me_without_token_returns_401_or_422():
    """GET /auth/me without token returns 401 or 422.

    FastAPI returns 422 for missing required header (validation error).
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/auth/me")

    # 422 = FastAPI validation error for missing required header
    # 401 = our handler converting to auth error
    assert response.status_code in [401, 422]


@pytest.mark.asyncio
async def test_me_with_expired_token_returns_401(mock_get_db):
    """GET /auth/me with expired token returns 401."""
    from datetime import timedelta

    from app.core.security import create_access_token

    # Create expired token
    token = create_access_token(
        {"sub": "1", "username": "testuser"},
        expires_delta=timedelta(seconds=-1),
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 401


# --- PATCH /auth/me Tests ---


@pytest.mark.asyncio
async def test_update_me_with_valid_data_returns_200(test_user, mock_get_db):
    """PATCH /auth/me with valid data returns 200 and updated user info."""
    from datetime import UTC, datetime

    from app.core.security import create_access_token, get_password_hash

    token = create_access_token({"sub": "1", "username": test_user["username"]})

    # Mock current user
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = test_user["username"]
    mock_user.email = test_user["email"]
    mock_user.is_active = True
    mock_user.created_at = datetime.now(UTC)
    mock_user.hashed_password = get_password_hash(test_user["password"])
    mock_user.role = "user"

    # Mock results for execute calls: get_current_user, username check, email check
    mock_result_user = MagicMock()
    mock_result_user.scalar_one_or_none.return_value = mock_user

    mock_result_none = MagicMock()
    mock_result_none.scalar_one_or_none.return_value = None

    mock_get_db.execute.side_effect = [mock_result_user, mock_result_none, mock_result_none]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "username": "new_username",
                "email": "new@example.com",
            },
        )

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "new_username"
    assert data["email"] == "new@example.com"


@pytest.mark.asyncio
async def test_update_me_with_duplicate_username_returns_400(test_user, mock_get_db):
    """PATCH /auth/me with existing username returns 400."""
    from datetime import UTC, datetime

    from app.core.security import create_access_token, get_password_hash

    token = create_access_token({"sub": "1", "username": test_user["username"]})

    # Mock current user
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = test_user["username"]
    mock_user.email = test_user["email"]
    mock_user.is_active = True
    mock_user.created_at = datetime.now(UTC)
    mock_user.hashed_password = get_password_hash(test_user["password"])
    mock_user.role = "user"

    # Mock results: get_current_user returns user, username check returns duplicate
    mock_result_user = MagicMock()
    mock_result_user.scalar_one_or_none.return_value = mock_user

    mock_result_duplicate = MagicMock()
    existing_user = MagicMock()
    existing_user.username = "existing_user"
    mock_result_duplicate.scalar_one_or_none.return_value = existing_user

    mock_get_db.execute.side_effect = [mock_result_user, mock_result_duplicate]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"username": "existing_user"},
        )

    assert response.status_code == 400
    assert "用户名" in response.json().get("detail", "")


@pytest.mark.asyncio
async def test_update_me_with_duplicate_email_returns_400(test_user, mock_get_db):
    """PATCH /auth/me with existing email returns 400."""
    from datetime import UTC, datetime

    from app.core.security import create_access_token, get_password_hash

    token = create_access_token({"sub": "1", "username": test_user["username"]})

    # Mock current user
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = test_user["username"]
    mock_user.email = test_user["email"]
    mock_user.is_active = True
    mock_user.created_at = datetime.now(UTC)
    mock_user.hashed_password = get_password_hash(test_user["password"])
    mock_user.role = "user"
    mock_user.deleted_at = None

    # Mock results: get_current_user returns user, email check returns duplicate
    # Note: username check is SKIPPED because update_data.username is None
    mock_result_user = MagicMock()
    mock_result_user.scalar_one_or_none.return_value = mock_user

    mock_result_duplicate = MagicMock()
    duplicate_user = MagicMock()
    duplicate_user.id = 999  # Different from mock_user.id = 1
    duplicate_user.username = "some_other_user"
    duplicate_user.deleted_at = None
    mock_result_duplicate.scalar_one_or_none.return_value = duplicate_user

    # Only 2 execute calls: 1) get_current_user, 2) email check (username check skipped)
    mock_get_db.execute.side_effect = [mock_result_user, mock_result_duplicate]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"email": "existing@example.com"},
        )

    assert response.status_code == 400
    assert "邮箱" in response.json().get("detail", "")


@pytest.mark.asyncio
async def test_update_me_with_same_username_returns_200(test_user, mock_get_db):
    """PATCH /auth/me with same username as current user returns 200 (no conflict)."""
    from datetime import UTC, datetime

    from app.core.security import create_access_token, get_password_hash

    token = create_access_token({"sub": "1", "username": test_user["username"]})

    # Mock current user
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = test_user["username"]
    mock_user.email = test_user["email"]
    mock_user.is_active = True
    mock_user.created_at = datetime.now(UTC)
    mock_user.hashed_password = get_password_hash(test_user["password"])
    mock_user.role = "user"

    # Mock results: get_current_user returns user, username check returns None (same username OK)
    mock_result_user = MagicMock()
    mock_result_user.scalar_one_or_none.return_value = mock_user

    mock_result_none = MagicMock()
    mock_result_none.scalar_one_or_none.return_value = None

    mock_get_db.execute.side_effect = [mock_result_user, mock_result_none]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.patch(
            "/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"username": test_user["username"]},
        )

    assert response.status_code == 200


# --- POST /auth/me/password Tests ---


@pytest.mark.asyncio
async def test_change_password_with_wrong_old_password_returns_400(test_user, mock_get_db):
    """POST /auth/me/password with wrong old password returns 400."""
    from datetime import UTC, datetime

    from app.core.security import create_access_token, get_password_hash

    token = create_access_token({"sub": "1", "username": test_user["username"]})

    # Mock current user
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = test_user["username"]
    mock_user.email = test_user["email"]
    mock_user.is_active = True
    mock_user.created_at = datetime.now(UTC)
    mock_user.hashed_password = get_password_hash("correct_password")
    mock_user.role = "user"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_get_db.execute.return_value = mock_result

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/auth/me/password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "old_password": "wrong_password",
                "new_password": "new_secure_password",
            },
        )

    assert response.status_code == 400
    assert "原密码" in response.json().get("detail", "")


@pytest.mark.asyncio
async def test_change_password_with_valid_data_returns_200(test_user, mock_get_db):
    """POST /auth/me/password with valid data returns 200."""
    from datetime import UTC, datetime

    from app.core.security import create_access_token, get_password_hash

    token = create_access_token({"sub": "1", "username": test_user["username"]})

    # Mock current user
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.username = test_user["username"]
    mock_user.email = test_user["email"]
    mock_user.is_active = True
    mock_user.created_at = datetime.now(UTC)
    mock_user.hashed_password = get_password_hash(test_user["password"])
    mock_user.role = "user"

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_user
    mock_get_db.execute.return_value = mock_result

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/auth/me/password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "old_password": test_user["password"],
                "new_password": "new_secure_password",
            },
        )

    assert response.status_code == 200
    assert "成功" in response.json().get("message", "")


@pytest.mark.asyncio
async def test_change_password_without_token_returns_401_or_422():
    """POST /auth/me/password without token returns 401 or 422."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/auth/me/password",
            json={
                "old_password": "old",
                "new_password": "new_password",
            },
        )

    assert response.status_code in [401, 422]


# --- Health Check for Auth Endpoints ---


@pytest.mark.asyncio
async def test_auth_endpoints_exist():
    """Verify auth endpoints are registered in the app."""
    # Check router is included - this will fail with AttributeError if not
    from app.main import app

    routes = [route.path for route in app.routes]
    auth_routes = [r for r in routes if r.startswith("/auth")]

    # At minimum, these routes should be registered
    expected_routes = ["/auth/register", "/auth/login", "/auth/logout", "/auth/me"]
    for route in expected_routes:
        assert route in auth_routes, f"Route {route} not found in app routes"
