"""WeChat OAuth login API routes.

Provides WeChat QR code login, callback handling, and account binding.
Feature-flagged: returns 503 when WeChat login is not configured.
"""
import logging
import secrets
from datetime import UTC, datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.audit import log_audit
from app.core.security import create_access_token, create_session, get_password_hash
from app.database import get_db
from app.models.user import User
from app.schemas.auth import TokenResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth/wechat", tags=["wechat"])

# In-memory state cache (short-lived, expires in 10 minutes)
_state_cache: dict[str, datetime] = {}

WECHAT_QR_CONNECT_URL = "https://open.weixin.qq.com/connect/qrconnect"
WECHAT_TOKEN_URL = "https://api.weixin.qq.com/sns/oauth2/access_token"
WECHAT_USERINFO_URL = "https://api.weixin.qq.com/sns/userinfo"


def _cleanup_expired_states() -> None:
    """Remove expired states from cache."""
    now = datetime.now(UTC)
    expired = [k for k, v in _state_cache.items() if now - v > timedelta(minutes=10)]
    for k in expired:
        del _state_cache[k]


def _check_wechat_enabled() -> None:
    """Raise 503 if WeChat login is not configured."""
    if not settings.wechat_login_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="微信登录未启用",
        )
    if not settings.wechat_app_id or not settings.wechat_app_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="微信登录配置不完整",
        )


@router.get("/qr")
async def get_wechat_qr_url():
    """Generate WeChat QR code authorization URL.

    Returns a URL for the user to scan with WeChat.
    The state parameter is randomly generated and cached for 10 minutes.
    """
    _check_wechat_enabled()

    _cleanup_expired_states()
    state = secrets.token_urlsafe(32)
    _state_cache[state] = datetime.now(UTC)

    redirect_uri = settings.wechat_redirect_uri or "http://localhost:8000/auth/wechat/callback"
    qr_url = (
        f"{WECHAT_QR_CONNECT_URL}"
        f"?appid={settings.wechat_app_id}"
        f"&redirect_uri={redirect_uri}"
        f"&response_type=code"
        f"&scope=snsapi_login"
        f"&state={state}"
    )

    return {"qr_url": qr_url, "state": state}


@router.get("/callback")
async def wechat_callback(
    code: str,
    state: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle WeChat OAuth callback.

    Exchanges code for access_token and openid.
    If the openid is already bound to a user, logs them in.
    Otherwise, returns a temporary token for binding/registration.
    """
    _check_wechat_enabled()

    # Validate state
    _cleanup_expired_states()
    if state not in _state_cache:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的 state 参数或已过期",
        )
    del _state_cache[state]

    # Exchange code for token
    async with httpx.AsyncClient() as client:
        token_resp = await client.get(
            WECHAT_TOKEN_URL,
            params={
                "appid": settings.wechat_app_id,
                "secret": settings.wechat_app_secret,
                "code": code,
                "grant_type": "authorization_code",
            },
        )

    token_data = token_resp.json()
    if "errcode" in token_data:
        logger.error(f"WeChat token exchange failed: {token_data}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"微信授权失败: {token_data.get('errmsg', '未知错误')}",
        )

    openid = token_data.get("openid")
    if not openid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无法获取微信 openid",
        )

    # Check if openid is already bound
    result = await db.execute(
        select(User).where(User.wechat_openid == openid, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if user:
        # Already bound - login
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户已被禁用",
            )

        access_token = create_access_token(
            data={"sub": str(user.id), "username": user.username},
            expires_delta=timedelta(hours=1),
        )

        device = request.headers.get("user-agent", "")[:200]
        ip_address = request.client.host if request.client else ""
        await create_session(
            user_id=user.id,
            token=access_token,
            device=device,
            ip_address=ip_address,
            db=db,
        )

        await log_audit(
            db=db,
            action="auth.login",
            actor_user_id=user.id,
            target_type="user",
            target_id=user.id,
            details={"username": user.username, "method": "wechat"},
            ip_address=ip_address,
            user_agent=request.headers.get("user-agent", "")[:512],
            commit=True,
        )

        return TokenResponse(access_token=access_token)

    # Not bound - return temporary token for binding
    temp_token = create_access_token(
        data={"wechat_openid": openid, "temp": True},
        expires_delta=timedelta(minutes=10),
    )

    return {
        "temp_token": temp_token,
        "message": "微信账号未绑定，请绑定现有账号或注册新账号",
    }


@router.post("/bind", response_model=TokenResponse)
async def bind_wechat_account(
    temp_token: str,
    username: str,
    password: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Bind WeChat account to an existing user.

    Args:
        temp_token: Temporary token from callback
        username: Existing username
        password: Existing password
    """
    _check_wechat_enabled()

    from app.core.security import decode_access_token, verify_password

    payload = decode_access_token(temp_token)
    if not payload or not payload.get("temp") or not payload.get("wechat_openid"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的临时令牌",
        )

    openid = payload["wechat_openid"]

    # Check if openid already bound
    existing = await db.execute(
        select(User).where(User.wechat_openid == openid, User.deleted_at.is_(None))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该微信账号已绑定其他用户",
        )

    # Find user by username
    result = await db.execute(
        select(User).where(User.username == username, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户已被禁用",
        )

    # Check if openid is already bound to another user
    conflict = await db.execute(
        select(User).where(
            User.wechat_openid == openid,
            User.id != user.id,
            User.deleted_at.is_(None),
        )
    )
    if conflict.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该微信 openid 已绑定其他用户",
        )

    # Bind openid
    user.wechat_openid = openid
    user.wechat_bind_at = datetime.now(UTC)
    await db.commit()

    # Create session
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username},
        expires_delta=timedelta(hours=1),
    )

    device = request.headers.get("user-agent", "")[:200]
    ip_address = request.client.host if request.client else ""
    await create_session(
        user_id=user.id,
        token=access_token,
        device=device,
        ip_address=ip_address,
        db=db,
    )

    await log_audit(
        db=db,
        action="user.wechat_bind",
        actor_user_id=user.id,
        target_type="user",
        target_id=user.id,
        details={"username": user.username, "method": "bind_existing"},
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent", "")[:512],
        commit=True,
    )

    return TokenResponse(access_token=access_token)


@router.post("/register", response_model=TokenResponse)
async def register_with_wechat(
    temp_token: str,
    username: str,
    email: str,
    password: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user and bind WeChat account.

    Args:
        temp_token: Temporary token from callback
        username: New username
        email: New email
        password: New password
    """
    _check_wechat_enabled()

    from app.core.security import decode_access_token

    payload = decode_access_token(temp_token)
    if not payload or not payload.get("temp") or not payload.get("wechat_openid"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的临时令牌",
        )

    openid = payload["wechat_openid"]

    # Check if openid already bound
    existing = await db.execute(
        select(User).where(User.wechat_openid == openid, User.deleted_at.is_(None))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="该微信账号已绑定其他用户",
        )

    # Check username uniqueness
    username_result = await db.execute(
        select(User).where(User.username == username, User.deleted_at.is_(None))
    )
    if username_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已注册",
        )

    # Check email uniqueness
    email_result = await db.execute(
        select(User).where(User.email == email, User.deleted_at.is_(None))
    )
    if email_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已注册",
        )

    # Create user
    hashed_password = get_password_hash(password)
    new_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        is_active=True,
        wechat_openid=openid,
        wechat_bind_at=datetime.now(UTC),
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # Create session
    access_token = create_access_token(
        data={"sub": str(new_user.id), "username": new_user.username},
        expires_delta=timedelta(hours=1),
    )

    device = request.headers.get("user-agent", "")[:200]
    ip_address = request.client.host if request.client else ""
    await create_session(
        user_id=new_user.id,
        token=access_token,
        device=device,
        ip_address=ip_address,
        db=db,
    )

    await log_audit(
        db=db,
        action="user.register",
        actor_user_id=new_user.id,
        target_type="user",
        target_id=new_user.id,
        details={"username": new_user.username, "email": new_user.email, "method": "wechat"},
        ip_address=ip_address,
        user_agent=request.headers.get("user-agent", "")[:512],
        commit=True,
    )

    return TokenResponse(access_token=access_token)
