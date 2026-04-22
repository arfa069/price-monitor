"""Alert schemas."""
from datetime import datetime
from typing import Optional
from decimal import Decimal
from pydantic import BaseModel, Field


class AlertCreate(BaseModel):
    """Schema for creating an alert."""
    product_id: int = Field(..., description="Product ID to alert on")
    threshold_percent: Optional[Decimal] = Field(default=Decimal("5.00"), ge=0, le=100, description="Trigger threshold percentage")
    active: bool = Field(default=True, description="Whether alert is active")


class AlertUpdate(BaseModel):
    """Schema for updating an alert."""
    threshold_percent: Optional[Decimal] = Field(default=None, ge=0, le=100)
    active: Optional[bool] = None


class AlertResponse(BaseModel):
    """Schema for alert response."""
    id: int
    product_id: int
    alert_type: str
    threshold_percent: Optional[Decimal]
    last_notified_at: Optional[datetime]
    last_notified_price: Optional[Decimal]
    active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}