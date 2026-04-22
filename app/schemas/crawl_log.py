"""Crawl log schemas."""
from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel


class CrawlLogResponse(BaseModel):
    """Schema for crawl log response."""
    id: int
    product_id: Optional[int]
    platform: Optional[str]
    status: Optional[str]
    price: Optional[Decimal]
    currency: Optional[str]
    timestamp: datetime
    error_message: Optional[str]

    model_config = {"from_attributes": True}