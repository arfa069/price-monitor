"""Price history schemas."""
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class PriceHistoryResponse(BaseModel):
    """Schema for price history record."""
    id: int
    product_id: int
    price: Decimal
    currency: str
    scraped_at: datetime

    model_config = {"from_attributes": True}


class PriceHistorySummary(BaseModel):
    """Summary of price history for a product."""
    id: int
    price: Decimal
    currency: str
    scraped_at: datetime

    model_config = {"from_attributes": True}
