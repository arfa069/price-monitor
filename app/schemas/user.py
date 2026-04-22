"""User configuration schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class UserConfigCreate(BaseModel):
    """Schema for creating user configuration."""
    feishu_webhook_url: str = Field(..., description="Feishu webhook URL for notifications")
    crawl_frequency_hours: int = Field(default=1, ge=1, le=168, description="Crawl frequency in hours")
    data_retention_days: int = Field(default=365, ge=1, le=3650, description="Data retention period in days")


class UserConfigUpdate(BaseModel):
    """Schema for updating user configuration."""
    feishu_webhook_url: Optional[str] = Field(default=None, description="Feishu webhook URL")
    crawl_frequency_hours: Optional[int] = Field(default=None, ge=1, le=168)
    data_retention_days: Optional[int] = Field(default=None, ge=1, le=3650)


class UserConfigResponse(BaseModel):
    """Schema for user configuration response."""
    id: int
    username: str
    feishu_webhook_url: str
    crawl_frequency_hours: int
    data_retention_days: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}