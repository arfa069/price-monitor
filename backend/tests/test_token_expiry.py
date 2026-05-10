"""Tests verifying token expiry is unified to 60 minutes across constants and login."""
from datetime import UTC, datetime, timedelta

from jose import jwt

from app.core.security import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    SECRET_KEY,
    create_access_token,
)


def test_token_expire_constant_is_60_minutes():
    """常量应统一为 60 分钟，与登录接口的 1 小时一致。"""
    assert ACCESS_TOKEN_EXPIRE_MINUTES == 60


def test_default_token_expires_in_60_minutes():
    """create_access_token 不传 expires_delta 时应使用 60 分钟。"""
    before = datetime.now(UTC)
    token = create_access_token({"sub": "1"})
    after = datetime.now(UTC)

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    exp_dt = datetime.fromtimestamp(payload["exp"], tz=UTC)

    # exp 应该在 [before+60min, after+60min] 范围内
    assert exp_dt >= before + timedelta(minutes=60) - timedelta(seconds=2)
    assert exp_dt <= after + timedelta(minutes=60) + timedelta(seconds=2)
