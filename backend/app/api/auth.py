"""Authentication API routes.

提供用户认证相关功能：注册、登录、登出、获取当前用户信息。

## Endpoints

| Method | Path | Description | Auth Required |
|--------|------|-------------|---------------|
| POST | /auth/register | Register new user | No |
| POST | /auth/login | User login | No |
| POST | /auth/logout | User logout | Yes |
| GET | /auth/me | Get current user info | Yes |

## Error Codes

| Status | Description |
|--------|-------------|
| 201 | Registration successful |
| 200 | Login/logout/me successful |
| 400 | Username or email already registered |
| 401 | Authentication failed |
| 422 | Validation failed |
| 429 | Too many requests (locked for 15 min after 5 failures) |

## Usage Examples

```bash
# Register
curl -X POST http://localhost:8000/auth/register \\
    -H "Content-Type: application/json" \\
    -d '{"username": "testuser", "email": "test@example.com", "password": "123456"}'

# Login
curl -X POST http://localhost:8000/auth/login \\
    -H "Content-Type: application/json" \\
    -d '{"username": "testuser", "password": "123456"}'

# Get current user (requires token)
curl -X GET http://localhost:8000/auth/me \\
    -H "Authorization: Bearer <token>"
```
"""
import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    clear_login_attempts,
    create_access_token,
    get_current_user,
    get_password_hash,
    is_account_locked,
    record_failed_login,
    verify_password,
)
from app.database import get_db
from app.models.user import User
from app.schemas.auth import (
    MessageResponse,
    PasswordChange,
    ProfileUpdate,
    TokenResponse,
    UserLogin,
    UserRegister,
    UserResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

# Token expiration time
TOKEN_EXPIRE_HOURS = 1


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED, tags=["auth"])
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user.

    Creates a new user account with username, email, and password.

    Args:
        user_data: User registration data (username, email, password)

    Returns:
        UserResponse: Created user information

    Raises:
        HTTPException 400: Username or email already exists
        HTTPException 422: Validation error (password too short, invalid email)

    Example:
        curl -X POST http://localhost:8000/auth/register \\
            -H "Content-Type: application/json" \\
            -d '{"username": "testuser", "email": "test@example.com", "password": "123456"}'
    """
    # Check if username already exists
    result = await db.execute(select(User).where(User.username == user_data.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已注册",
        )

    # Check if email already exists
    result = await db.execute(select(User).where(User.email == user_data.email))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已注册",
        )

    # Create new user
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        is_active=True,
    )

    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    logger.info(f"User registered: {user_data.username}")
    return new_user


@router.post("/login", response_model=TokenResponse, tags=["auth"])
async def login(login_data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login and get access token.

    Authenticates user with username and password, returns JWT token.

    Args:
        login_data: Login credentials (username, password)

    Returns:
        TokenResponse: JWT access token (24 hour validity)

    Raises:
        HTTPException 401: Invalid username or password
        HTTPException 429: Account locked (5 failed attempts, 15 min lockout)

    Example:
        curl -X POST http://localhost:8000/auth/login \\
            -H "Content-Type: application/json" \\
            -d '{"username": "testuser", "password": "123456"}'
    """
    # Check if account is locked
    is_locked, minutes_remaining = await is_account_locked(login_data.username)
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"登录尝试次数过多，请 {minutes_remaining} 分钟后再试",
        )

    # Find user by username
    result = await db.execute(select(User).where(User.username == login_data.username))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(login_data.password, user.hashed_password):
        # Record failed attempt
        await record_failed_login(login_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户已被禁用",
        )

    # Clear failed login attempts
    await clear_login_attempts(login_data.username)

    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username},
        expires_delta=timedelta(hours=TOKEN_EXPIRE_HOURS),
    )

    logger.info(f"User logged in: {user.username}")
    return TokenResponse(access_token=access_token)


@router.post("/logout", response_model=MessageResponse, tags=["auth"])
async def logout(current_user: User = Depends(get_current_user)):
    """Logout current user.

    Since JWT tokens are stateless, this endpoint just returns success.
    Client should remove the stored token.

    Args:
        current_user: Authenticated user (from JWT token)

    Returns:
        MessageResponse: Logout success message

    Example:
        curl -X POST http://localhost:8000/auth/logout \\
            -H "Authorization: Bearer <token>"
    """
    logger.info(f"User logged out: {current_user.username}")
    return MessageResponse(message="登出成功")


@router.get("/me", response_model=UserResponse, tags=["auth"])
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user information.

    Returns the authenticated user's profile information.

    Args:
        current_user: Authenticated user (from JWT token)

    Returns:
        UserResponse: Current user profile

    Example:
        curl -X GET http://localhost:8000/auth/me \\
            -H "Authorization: Bearer <token>"
    """
    return current_user


@router.patch("/me", response_model=UserResponse, tags=["auth"])
async def update_me(
    update_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user's profile (username, email).

    Args:
        update_data: Profile update data (username, email)
        current_user: Authenticated user (from JWT token)
        db: Database session

    Returns:
        UserResponse: Updated user profile

    Raises:
        HTTPException 400: Username or email already exists

    Example:
        curl -X PATCH http://localhost:8000/auth/me \\
            -H "Authorization: Bearer <token>" \\
            -H "Content-Type: application/json" \\
            -d '{"username": "new_username", "email": "new@example.com"}'
    """
    # Check username conflict (only if username is being changed)
    if update_data.username and update_data.username != current_user.username:
        result = await db.execute(
            select(User).where(
                User.username == update_data.username,
                User.id != current_user.id,
                User.deleted_at.is_(None),
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="用户名已存在",
            )

    # Check email conflict (only if email is being changed)
    if update_data.email and update_data.email != current_user.email:
        result = await db.execute(
            select(User).where(
                User.email == update_data.email,
                User.id != current_user.id,
                User.deleted_at.is_(None),
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="邮箱已存在",
            )

    # Update fields
    if update_data.username:
        current_user.username = update_data.username
    if update_data.email:
        current_user.email = update_data.email

    await db.commit()
    await db.refresh(current_user)
    logger.info(f"Profile updated for user: {current_user.username}")
    return current_user


@router.post("/me/password", response_model=MessageResponse, tags=["auth"])
async def change_password(
    password_data: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change current user's password.

    Args:
        password_data: Password change data (old_password, new_password)
        current_user: Authenticated user (from JWT token)
        db: Database session

    Returns:
        MessageResponse: Success message

    Raises:
        HTTPException 400: Old password is incorrect

    Example:
        curl -X POST http://localhost:8000/auth/me/password \\
            -H "Authorization: Bearer <token>" \\
            -H "Content-Type: application/json" \\
            -d '{"old_password": "old_password", "new_password": "new_secure_password"}'
    """
    # Verify old password
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误",
        )

    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    await db.commit()

    logger.info(f"Password changed for user: {current_user.username}")
    return MessageResponse(message="密码修改成功")
