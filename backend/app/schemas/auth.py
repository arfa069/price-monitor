"""Authentication schemas for request/response validation."""
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    """Request schema for user registration."""
    username: str = Field(..., min_length=3, max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    password: str = Field(..., min_length=6, max_length=100, description="密码")

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        """Validate username: alphanumeric and underscore only."""
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("用户名只能包含字母、数字、下划线和连字符")
        return v.strip()


class UserLogin(BaseModel):
    """Request schema for user login."""
    username: str = Field(..., description="用户名")
    password: str = Field(..., description="密码")


class UserResponse(BaseModel):
    """Response schema for user information."""
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Response schema for authentication token."""
    access_token: str
    token_type: str = "bearer"


class ProfileUpdate(BaseModel):
    """Schema for updating current user's profile (username, email only)."""
    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: EmailStr | None = None


class PasswordChange(BaseModel):
    """Schema for password change."""
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=100)


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str


class LoginLogResponse(BaseModel):
    """Response schema for login history."""
    id: int
    ip_address: str | None
    user_agent: str | None
    created_at: datetime
    model_config = {"from_attributes": True}
