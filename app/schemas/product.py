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
    platform: Optional[str] = Field(default=None, pattern="^(taobao|jd|amazon)$")
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


class ProductListResponse(BaseModel):
    """Paginated product list response."""
    items: List[ProductResponse]
    total: int


class ProductBatchCreateItem(BaseModel):
    """Single item for batch create."""
    url: str = Field(..., description="Product URL")
    platform: str = Field(..., pattern="^(taobao|jd|amazon)$", description="Platform")
    title: Optional[str] = None


class ProductBatchCreate(BaseModel):
    """Batch create products."""
    items: List[ProductBatchCreateItem] = Field(..., max_length=100)


class BatchOperationResult(BaseModel):
    """Result of a single batch operation item."""
    id: Optional[int] = None
    url: Optional[str] = None
    success: bool
    error: Optional[str] = None


class ProductBatchUpdate(BaseModel):
    """Batch update products."""
    ids: List[int] = Field(..., max_length=100)
    active: Optional[bool] = None


class ProductBatchDelete(BaseModel):
    """Batch delete products."""
    ids: List[int] = Field(..., max_length=100)