"""Product schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl
from app.schemas.price_history import PriceHistorySummary
from app.schemas.alert import AlertResponse


class ProductCreate(BaseModel):
    """Schema for creating a product to track."""
    platform: str = Field(..., pattern="^(taobao|jd|amazon)$", description="Platform: taobao, jd, or amazon")
    url: str = Field(..., description="Product URL")
    title: Optional[str] = Field(default=None, description="Product title (auto-fetched if not provided)")
    active: bool = Field(default=True, description="Whether monitoring is active")


class ProductUpdate(BaseModel):
    """Schema for updating a product."""
    title: Optional[str] = None
    active: Optional[bool] = None
    url: Optional[str] = None


class ProductResponse(BaseModel):
    """Schema for product response."""
    id: int
    user_id: int
    platform: str
    url: str
    title: Optional[str]
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductDetail(ProductResponse):
    """Schema for product detail with relationships."""
    price_history: Optional[List[PriceHistorySummary]] = None
    alerts: Optional[List[AlertResponse]] = None