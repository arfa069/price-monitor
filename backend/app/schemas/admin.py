"""Admin API schemas."""
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for creating a user (admin)."""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)
    role: str = Field(default="user")


class AdminUserUpdate(BaseModel):
    """Schema for admin updating a user (includes role and is_active)."""
    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: EmailStr | None = None
    role: str | None = None
    is_active: bool | None = None  # True=恢复, False=软删除


class AdminUserResponse(BaseModel):
    """Schema for user response (admin)."""
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class AdminUserListResponse(BaseModel):
    """Schema for paginated user list."""
    items: list[AdminUserResponse]
    total: int
    page: int
    page_size: int