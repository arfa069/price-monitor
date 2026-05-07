"""Tests for session management."""
import hashlib
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.database import get_db
from app.main import app


@pytest.fixture
def mock_db_session():
    """Mock database session for session tests."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    session.refresh = AsyncMock()
    session.delete = AsyncMock()
    return session


@pytest.fixture
def mock_get_db(mock_db_session):
    """Override get_db dependency with mock session."""
    async def _override():
        yield mock_db_session
    app.dependency_overrides[get_db] = _override
    yield mock_db_session
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def test_user():
    """Test user data for authentication tests."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123",
    }


# --- Session Model Tests ---


@pytest.mark.asyncio
async def test_create_session(mock_db_session, test_user):
    """Test creating a new session."""
    from datetime import UTC, datetime
    from app.core.security import create_session

    token = "test_token_123"
    device = "Chrome on Windows"
    ip_address = "192.168.1.1"

    # Mock: user has no existing sessions
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db_session.execute.return_value = mock_result

    session = await create_session(
        user_id=1,
        token=token,
        device=device,
        ip_address=ip_address,
        db=mock_db_session,
    )

    assert session is not None
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_session_max_5_removes_oldest(mock_db_session):
    """Test that creating 6 sessions removes the oldest."""
    from app.core.security import create_session

    # Mock: user already has 5 sessions
    existing_sessions = [MagicMock(id=i+1) for i in range(5)]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = existing_sessions
    mock_db_session.execute.return_value = mock_result

    session = await create_session(
        user_id=1,
        token="token_6",
        device="New Device",
        ip_address="192.168.1.100",
        db=mock_db_session,
    )

    # Should delete the oldest (first) session
    assert mock_db_session.delete.call_count >= 1


@pytest.mark.asyncio
async def test_get_user_sessions(mock_db_session):
    """Test getting all sessions for a user."""
    from app.core.security import get_user_sessions

    # Mock: return 3 sessions
    mock_sessions = [MagicMock(id=i+1, user_id=1) for i in range(3)]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = mock_sessions
    mock_db_session.execute.return_value = mock_result

    sessions = await get_user_sessions(1, mock_db_session)

    assert len(sessions) == 3


@pytest.mark.asyncio
async def test_delete_session(mock_db_session):
    """Test deleting a specific session."""
    from app.core.security import delete_session

    # Mock: session exists
    mock_session = MagicMock(id=1, user_id=1)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = mock_session
    mock_db_session.execute.return_value = mock_result

    deleted = await delete_session(1, 1, mock_db_session)

    assert deleted is True
    mock_db_session.delete.assert_called_once_with(mock_session)


@pytest.mark.asyncio
async def test_delete_session_not_found(mock_db_session):
    """Test deleting a non-existent session."""
    from app.core.security import delete_session

    # Mock: session not found
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result

    deleted = await delete_session(9999, 1, mock_db_session)

    assert deleted is False


@pytest.mark.asyncio
async def test_delete_other_sessions(mock_db_session):
    """Test deleting all sessions except the current one."""
    from app.core.security import delete_other_sessions

    # Mock: return 3 sessions to delete
    other_sessions = [MagicMock(id=i+2, user_id=1) for i in range(3)]
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = other_sessions
    mock_db_session.execute.return_value = mock_result

    count = await delete_other_sessions(1, 1, mock_db_session)

    assert count == 3
    assert mock_db_session.delete.call_count == 3


@pytest.mark.asyncio
async def test_parse_device():
    """Test parsing device from user agent."""
    from app.core.security import parse_device

    assert parse_device("") == "Unknown"
    assert parse_device(None) == "Unknown"
    assert parse_device("Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0") == "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
    # Test truncation
    long_ua = "A" * 300
    assert parse_device(long_ua) == "A" * 200


# --- API Endpoint Tests ---


@pytest.mark.asyncio
async def test_session_response_model():
    """Test SessionResponse model can be instantiated."""
    from datetime import UTC, datetime
    from app.api.auth import SessionResponse

    session_data = {
        "id": 1,
        "device": "Chrome on Windows",
        "ip_address": "192.168.1.1",
        "last_active_at": datetime.now(UTC),
        "created_at": datetime.now(UTC),
    }

    response = SessionResponse(**session_data)
    assert response.id == 1
    assert response.device == "Chrome on Windows"
