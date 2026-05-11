"""Security utilities: password hashing and JWT token handling."""
import asyncio
from datetime import UTC, datetime, timedelta
from typing import Any
import hashlib

import redis.asyncio as redis
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.user import User

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT settings
SECRET_KEY = settings.jwt_secret_key
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Login attempt tracking (Redis-backed)
MAX_LOGIN_ATTEMPTS = 5
LOCKOUT_DURATION_SECONDS = 900  # 15 minutes

_redis_client: redis.Redis | None = None
_redis_loop: asyncio.AbstractEventLoop | None = None


async def _get_redis() -> redis.Redis:
    """Get or create Redis client (connection reused per event loop)."""
    global _redis_client, _redis_loop
    current_loop = asyncio.get_running_loop()
    if _redis_client is None or _redis_loop is not current_loop:
        _redis_client = redis.from_url(settings.redis_url_with_password)
        _redis_loop = current_loop
    return _redis_client


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


async def is_account_locked(username: str) -> tuple[bool, int]:
    """Check if account is locked due to too many failed attempts.

    Returns:
        tuple of (is_locked, minutes_remaining)
    """
    redis_client = await _get_redis()
    key = f"login_attempts:{username}"
    count = await redis_client.get(key)
    if count is None:
        return False, 0

    count_int = int(count)
    if count_int >= MAX_LOGIN_ATTEMPTS:
        ttl = await redis_client.ttl(key)
        minutes_remaining = max(1, int(ttl / 60)) if ttl > 0 else 1
        return True, minutes_remaining

    return False, 0


async def record_failed_login(username: str) -> None:
    """Record a failed login attempt."""
    redis_client = await _get_redis()
    key = f"login_attempts:{username}"
    count = await redis_client.incr(key)
    if count == 1:
        await redis_client.expire(key, LOCKOUT_DURATION_SECONDS)


async def clear_login_attempts(username: str) -> None:
    """Clear failed login attempts after successful login."""
    redis_client = await _get_redis()
    await redis_client.delete(f"login_attempts:{username}")


# OAuth2 scheme for token authentication (used by get_current_user and OpenAPI docs)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Dependency to get current authenticated user from JWT token.

    This is the single source of truth for user authentication across all routers.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证失败：Token 无效或已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    result = await db.execute(
        select(User).where(
            User.id == int(user_id),
            User.deleted_at.is_(None)  # 确保软删除用户立即失效
        )
    )
    user = result.scalar_one_or_none()

    if user is None or not user.is_active:
        raise credentials_exception

    return user


def parse_device(user_agent: str) -> str:
    """Parse browser and OS from User-Agent string."""
    if not user_agent:
        return "Unknown"
    return user_agent[:200]


async def create_session(
    user_id: int,
    token: str,
    device: str,
    ip_address: str,
    db: AsyncSession,
) -> Session:
    """Create a new session for a user."""
    from app.models.session import Session

    token_hash = hashlib.sha256(token.encode()).hexdigest()

    # Check max sessions (5)
    result = await db.execute(
        select(Session).where(
            Session.user_id == user_id,
            Session.token_hash.isnot(None)
        ).order_by(Session.created_at)
    )
    existing = result.scalars().all()
    if len(existing) >= 5:
        await db.delete(existing[0])

    session = Session(
        user_id=user_id,
        token_hash=token_hash,
        device=device,
        ip_address=ip_address,
    )
    db.add(session)
    await db.commit()
    return session


async def get_user_sessions(user_id: int, db: AsyncSession) -> list[Session]:
    """Get all active sessions for a user."""
    from app.models.session import Session

    result = await db.execute(
        select(Session).where(Session.user_id == user_id)
    )
    return list(result.scalars().all())


async def delete_session(session_id: int, user_id: int, db: AsyncSession) -> bool:
    """Delete a specific session."""
    from app.models.session import Session

    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.user_id == user_id
        )
    )
    session = result.scalar_one_or_none()
    if not session:
        return False
    await db.delete(session)
    await db.commit()
    return True


async def delete_other_sessions(current_session_id: int, user_id: int, db: AsyncSession) -> int:
    """Delete all sessions except the current one."""
    from app.models.session import Session

    result = await db.execute(
        select(Session).where(
            Session.user_id == user_id,
            Session.id != current_session_id
        )
    )
    sessions = result.scalars().all()
    for s in sessions:
        await db.delete(s)
    await db.commit()
    return len(sessions)


def require_role(*allowed_roles: str):
    """Decorator to require specific roles for an endpoint.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_role("admin", "super_admin"))])
    """
    async def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="需要管理员权限",
            )
        return current_user
    return role_checker
