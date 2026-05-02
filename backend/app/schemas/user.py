"""User configuration schemas."""
from datetime import datetime

from pydantic import BaseModel, Field


class UserConfigCreate(BaseModel):
    """Schema for creating user configuration."""
    feishu_webhook_url: str = Field(default="", description="Feishu webhook URL for notifications")
    data_retention_days: int = Field(default=365, ge=1, le=3650, description="Data retention period in days")


class UserConfigUpdate(BaseModel):
    """Schema for updating user configuration."""
    feishu_webhook_url: str | None = Field(default=None, description="Feishu webhook URL")
    data_retention_days: int | None = Field(default=None, ge=1, le=3650)


class UserConfigResponse(BaseModel):
    """Schema for user configuration response."""
    id: int
    username: str
    feishu_webhook_url: str | None = ""
    data_retention_days: int = 365
    created_at: datetime | None = None
    updated_at: datetime | None = None

    model_config = {"from_attributes": True}


class UserConfigDefaults(BaseModel):
    """Default configuration values."""
    data_retention_days: int = 365
