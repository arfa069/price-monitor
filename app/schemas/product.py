"""Product schemas."""
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

from app.schemas.alert import AlertResponse
from app.schemas.price_history import PriceHistorySummary


class ProductCreate(BaseModel):
    """Schema for creating a product to track."""
    platform: str = Field(..., pattern="^(taobao|jd|amazon)$", description="Platform: taobao, jd, or amazon")
    url: str = Field(..., description="Product URL")
    title: str | None = Field(default=None, description="Product title (auto-fetched if not provided)")
    active: bool = Field(default=True, description="Whether monitoring is active")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v.startswith("http://") and not v.startswith("https://"):
            raise ValueError("URL must start with http:// or https://")
        return v


class ProductUpdate(BaseModel):
    """Schema for updating a product."""
    title: str | None = None
    active: bool | None = None
    url: str | None = Field(default=None, description="Product URL (cannot be cleared)")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.strip()
        if not v:
            raise ValueError("URL cannot be empty")
        if not v.startswith("http://") and not v.startswith("https://"):
            raise ValueError("URL must start with http:// or https://")
        return v


class ProductResponse(BaseModel):
    """Schema for product response."""
    id: int
    user_id: int
    platform: str
    url: str
    title: str | None
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ProductDetail(ProductResponse):
    """Schema for product detail with relationships."""
    price_history: list[PriceHistorySummary] | None = None
    alerts: list[AlertResponse] | None = None


class ProductListResponse(BaseModel):
    """Paginated product list response."""
    items: list[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
    has_next: bool
    has_prev: bool


class ProductBatchCreateItem(BaseModel):
    """Single item for batch create."""
    url: str = Field(..., description="Product URL")
    platform: str | None = Field(default=None, pattern="^(taobao|jd|amazon)$", description="Platform (auto-detected if omitted)")
    title: str | None = None


class ProductBatchCreate(BaseModel):
    """Batch create products."""
    items: list[ProductBatchCreateItem] = Field(..., max_length=100)


class BatchOperationResult(BaseModel):
    """Result of a single batch operation item."""
    id: int | None = None
    url: str | None = None
    success: bool
    error: str | None = None


class ProductBatchUpdate(BaseModel):
    """Batch update products."""
    ids: list[int] = Field(..., max_length=100)
    active: bool | None = None


class ProductBatchDelete(BaseModel):
    """Batch delete products."""
    ids: list[int] = Field(..., max_length=100)
