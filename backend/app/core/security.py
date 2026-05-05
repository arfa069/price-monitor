"""Security utilities: password hashing and JWT token handling."""
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = "your-secret-key-change-in-production"  # TODO: Load from settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Login attempt tracking (in-memory for simplicity; use Redis in production)
_login_attempts: dict[str, list[datetime]] = {}
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_MINUTES = 15


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(UTC) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any] | None:
    """Decode and validate a JWT access token. Returns None if invalid/expired."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def is_account_locked(username: str) -> tuple[bool, int]:
    """Check if account is locked due to too many failed attempts.

    Returns:
        tuple of (is_locked, minutes_remaining)
    """
    now = datetime.now(UTC)
    if username not in _login_attempts:
        return False, 0

    # Clean old attempts
    _login_attempts[username] = [
        t for t in _login_attempts[username]
        if now - t < timedelta(minutes=LOCKOUT_DURATION_MINUTES)
    ]

    if len(_login_attempts[username]) >= MAX_LOGIN_ATTEMPTS:
        # Calculate minutes remaining
        oldest_attempt = min(_login_attempts[username])
        remaining = LOCKOUT_DURATION_MINUTES - int((now - oldest_attempt).total_seconds() / 60)
        return True, max(1, remaining)

    return False, 0


def record_failed_login(username: str) -> None:
    """Record a failed login attempt."""
    if username not in _login_attempts:
        _login_attempts[username] = []
    _login_attempts[username].append(datetime.now(UTC))


def clear_login_attempts(username: str) -> None:
    """Clear failed login attempts after successful login."""
    if username in _login_attempts:
        del _login_attempts[username]
