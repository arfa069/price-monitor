"""认证 API 路由：用户注册、登录、Token 管理。"""
import logging
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["认证"])

# 密码加密上下文
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# JWT 配置
SECRET_KEY = settings.jwt_secret_key  # 从环境变量读取
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 登录失败追踪（内存存储，生产环境建议使用 Redis）
_login_failures: dict[str, dict] = {}


# ============ 请求/响应模型 ============

class UserRegisterRequest(BaseModel):
    """用户注册请求模型。"""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=6, max_length=128, description="密码（至少6位）")


class UserRegisterResponse(BaseModel):
    """用户注册成功响应模型。"""
    id: int
    username: str
    email: str

    model_config = {"from_attributes": True}


class UserLoginRequest(BaseModel):
    """用户登录请求模型（支持 username 或 email）。"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")


class Token(BaseModel):
    """JWT Token 响应模型。"""
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token 解码后的数据。"""
    user_id: int | None = None


class UserProfileResponse(BaseModel):
    """用户资料响应模型。"""
    id: int
    username: str
    email: str
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# ============ 辅助函数 ============

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码是否匹配。"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """对密码进行哈希处理。"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """创建 JWT 访问令牌。"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def _is_account_locked(identifier: str) -> bool:
    """检查账户是否因连续登录失败而被锁定。"""
    if identifier not in _login_failures:
        return False
    record = _login_failures[identifier]
    if record["failures"] < 5:
        return False
    # 锁定15分钟后解锁
    lock_duration = timedelta(minutes=15)
    if datetime.now(timezone.utc) - record["last_failure"] < lock_duration:
        return True
    # 锁定已过期，重置
    del _login_failures[identifier]
    return False


def _record_login_failure(identifier: str) -> None:
    """记录登录失败次数。"""
    now = datetime.now(timezone.utc)
    if identifier not in _login_failures:
        _login_failures[identifier] = {"failures": 0, "last_failure": now}
    _login_failures[identifier]["failures"] += 1
    _login_failures[identifier]["last_failure"] = now


def _reset_login_failures(identifier: str) -> None:
    """重置登录失败计数。"""
    _login_failures.pop(identifier, None)


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """依赖项：从 JWT Token 获取当前用户。"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="认证失败：Token 无效或已过期",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.id == token_data.user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user


# ============ API 端点 ============

@router.post(
    "/register",
    response_model=UserRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="注册新用户",
    responses={
        201: {"description": "用户注册成功"},
        400: {"description": "用户名或邮箱已被注册"},
        422: {"description": "参数验证失败（密码太短、邮箱格式错误等）"},
    },
)
"""
注册新用户

创建一个新用户账户，包含用户名、邮箱和密码。

### 请求
- **Method**: `POST /auth/register`
- **Content-Type**: `application/json`

### 请求体
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名（3-50字符） |
| email | string | 是 | 邮箱地址（有效格式） |
| password | string | 是 | 密码（至少6位） |

### 响应状态码
- **201 Created**: 注册成功
- **400 Bad Request**: 用户名或邮箱已被注册
- **422 Unprocessable Entity**: 参数验证失败

### 示例
```bash
curl -X POST http://localhost:8000/auth/register \\
    -H "Content-Type: application/json" \\
    -d '{"username": "testuser", "email": "test@example.com", "password": "123456"}'
```

### 响应示例（成功）
```json
{
    "id": 1,
    "username": "testuser",
    "email": "test@example.com"
}
```
"""


async def register(
    user_data: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """注册新用户。"""
    # 检查用户名是否已存在
    result = await db.execute(
        select(User).where(User.username == user_data.username)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已注册",
        )

    # 检查邮箱是否已存在
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="邮箱已注册",
        )

    # 创建新用户
    hashed_password = get_password_hash(user_data.password)
    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    logger.info(f"用户注册成功: {user_data.username}")
    return UserRegisterResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
    )


@router.post(
    "/login",
    response_model=Token,
    summary="用户登录",
    responses={
        200: {"description": "登录成功，返回访问令牌"},
        401: {"description": "认证失败（用户名/密码错误或账户已锁定）"},
        429: {"description": "请求过于频繁（连续失败5次后锁定15分钟）"},
    },
)
"""
用户登录

通过用户名（或邮箱）和密码进行身份验证，返回 JWT 访问令牌。

### 请求
- **Method**: `POST /auth/login`
- **Content-Type**: `application/json` 或 `application/x-www-form-urlencoded`

### 请求体（JSON 格式）
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名或邮箱 |
| password | string | 是 | 密码 |

### 请求体（表单格式，OAuth2 标准）
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| username | string | 是 | 用户名或邮箱 |
| password | string | 是 | 密码 |

### 响应状态码
- **200 OK**: 登录成功，返回 JWT 令牌
- **401 Unauthorized**: 用户名或密码错误
- **429 Too Many Requests**: 账户已被锁定（连续5次失败后锁定15分钟）

### 示例
```bash
# JSON 格式
curl -X POST http://localhost:8000/auth/login \\
    -H "Content-Type: application/json" \\
    -d '{"username": "testuser", "password": "123456"}'

# 表单格式（OAuth2 标准）
curl -X POST http://localhost:8000/auth/login \\
    -d "username=testuser&password=123456"
```

### 响应示例（成功）
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer"
}
```

### 错误码
| 状态码 | 含义 | 详情 |
|--------|------|------|
| 401 | 认证失败 | 用户名或密码错误 |
| 429 | 账户锁定 | 连续5次失败后锁定15分钟 |
"""


async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """用户登录，返回 JWT 访问令牌。"""
    identifier = form_data.username

    # 检查账户是否被锁定
    if _is_account_locked(identifier):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="账户已锁定：连续登录失败5次，请15分钟后再试",
        )

    # 查询用户
    result = await db.execute(
        select(User).where(
            (User.username == identifier) | (User.email == identifier)
        )
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.hashed_password):
        _record_login_failure(identifier)
        remaining = 5 - _login_failures[identifier]["failures"]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"用户名或密码错误（剩余尝试次数: {remaining}）",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 登录成功，重置失败计数
    _reset_login_failures(identifier)

    # 创建访问令牌
    access_token = create_access_token(
        data={"sub": user.id, "username": user.username}
    )

    logger.info(f"用户登录成功: {user.username}")
    return Token(access_token=access_token, token_type="bearer")


@router.get(
    "/me",
    response_model=UserProfileResponse,
    summary="获取当前用户资料",
)
"""
获取当前登录用户的资料

需要提供有效的 JWT 访问令牌。

### 请求
- **Method**: `GET /auth/me`
- **Headers**: `Authorization: Bearer <access_token>`

### 示例
```bash
curl -X GET http://localhost:8000/auth/me \\
    -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 响应示例
```json
{
    "id": 1,
    "username": "testuser",
    "email": "test@example.com",
    "created_at": "2026-05-06T10:30:00Z"
}
```
"""


async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前登录用户的资料。"""
    return UserProfileResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        created_at=current_user.created_at,
    )


@router.post(
    "/refresh",
    response_model=Token,
    summary="刷新访问令牌",
)
"""
刷新访问令牌

使用当前有效的令牌获取新的访问令牌。

### 请求
- **Method**: `POST /auth/refresh`
- **Headers**: `Authorization: Bearer <access_token>`

### 示例
```bash
curl -X POST http://localhost:8000/auth/refresh \\
    -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```
"""


async def refresh_token(current_user: User = Depends(get_current_user)):
    """刷新访问令牌。"""
    access_token = create_access_token(
        data={"sub": current_user.id, "username": current_user.username}
    )
    return Token(access_token=access_token, token_type="bearer")
