"""Unit tests for security utilities: password hashing and JWT tokens."""
from datetime import timedelta

from app.core.security import (
    clear_login_attempts,
    create_access_token,
    decode_access_token,
    get_password_hash,
    is_account_locked,
    record_failed_login,
    verify_password,
)

# --- Password Hashing Tests ---


def test_hash_password_generates_unique_hashes():
    """hash_password generates a bcrypt hash that is not the plain password."""
    password = "test_password_123"
    hashed = get_password_hash(password)

    # Hash should not be the plain password
    assert hashed != password
    # Hash should be a bcrypt format (starts with $2b$)
    assert hashed.startswith("$2b$")


def test_verify_password_correct_password_succeeds():
    """verify_password returns True for correct password."""
    password = "correct_password"
    hashed = get_password_hash(password)

    assert verify_password(password, hashed) is True


def test_verify_password_wrong_password_fails():
    """verify_password returns False for wrong password."""
    password = "correct_password"
    wrong_password = "wrong_password"
    hashed = get_password_hash(password)

    assert verify_password(wrong_password, hashed) is False


def test_hash_password_different_for_same_input():
    """hash_password generates different hashes for same input (due to salt)."""
    password = "same_password"
    hash1 = get_password_hash(password)
    hash2 = get_password_hash(password)

    # Salt ensures different hashes
    assert hash1 != hash2
    # But both verify correctly
    assert verify_password(password, hash1) is True
    assert verify_password(password, hash2) is True


# --- JWT Token Tests ---


def test_create_access_token_generates_string_token():
    """create_access_token returns a string JWT token."""
    data = {"sub": "testuser"}
    token = create_access_token(data)

    assert isinstance(token, str)
    assert len(token) > 20
    # JWT format: header.payload.signature
    assert token.count(".") == 2


def test_decode_access_token_valid_token_succeeds():
    """decode_access_token returns payload for valid token."""
    data = {"sub": "testuser", "extra": "value"}
    token = create_access_token(data)

    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == "testuser"
    assert payload["extra"] == "value"
    assert "exp" in payload


def test_decode_access_token_expired_token_returns_none():
    """decode_access_token returns None for expired token."""
    data = {"sub": "testuser"}
    # Create token that expires immediately
    token = create_access_token(data, expires_delta=timedelta(seconds=-1))

    payload = decode_access_token(token)

    assert payload is None


def test_decode_access_token_invalid_signature_returns_none():
    """decode_access_token returns None for token with wrong signature."""
    # Create token with different secret (simulate tampering)
    from jose import jwt

    data = {"sub": "testuser"}
    fake_token = jwt.encode(data, "fake-secret-key", algorithm="HS256")

    payload = decode_access_token(fake_token)

    assert payload is None


def test_create_access_token_custom_expiry():
    """create_access_token respects custom expires_delta."""
    data = {"sub": "testuser"}
    token = create_access_token(data, expires_delta=timedelta(hours=1))

    payload = decode_access_token(token)

    assert payload is not None
    assert "exp" in payload


# --- Login Attempt Tracking Tests ---


def test_record_failed_login_tracks_attempt():
    """record_failed_login adds attempt to tracking dict."""
    username = "testuser_record"
    clear_login_attempts(username)  # Clean slate

    record_failed_login(username)

    is_locked, _ = is_account_locked(username)
    assert is_locked is False  # First attempt, not locked


def test_is_account_locked_after_max_attempts():
    """is_account_locked returns True after MAX_LOGIN_ATTEMPTS failures."""
    username = "testuser_locked"
    clear_login_attempts(username)

    # Simulate 5 failed attempts
    for _ in range(5):
        record_failed_login(username)

    is_locked, minutes_remaining = is_account_locked(username)

    assert is_locked is True
    assert minutes_remaining >= 1


def test_is_account_locked_false_before_max_attempts():
    """is_account_locked returns False before MAX_LOGIN_ATTEMPTS."""
    username = "testuser_safe"
    clear_login_attempts(username)

    # Only 3 attempts
    for _ in range(3):
        record_failed_login(username)

    is_locked, _ = is_account_locked(username)

    assert is_locked is False


def test_clear_login_attempts_resets_lockout():
    """clear_login_attempts removes all tracked attempts."""
    username = "testuser_clear"
    clear_login_attempts(username)

    # Add 5 failed attempts
    for _ in range(5):
        record_failed_login(username)

    # Clear attempts
    clear_login_attempts(username)

    is_locked, _ = is_account_locked(username)
    assert is_locked is False
