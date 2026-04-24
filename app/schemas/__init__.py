"""API schemas."""
from app.schemas.alert import AlertCreate, AlertResponse, AlertUpdate
from app.schemas.crawl_log import CrawlLogResponse
from app.schemas.price_history import PriceHistoryResponse, PriceHistorySummary
from app.schemas.product import (
    ProductCreate,
    ProductDetail,
    ProductResponse,
    ProductUpdate,
)
from app.schemas.user import UserConfigCreate, UserConfigResponse, UserConfigUpdate

__all__ = [
    "UserConfigCreate",
    "UserConfigUpdate",
    "UserConfigResponse",
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    "ProductDetail",
    "AlertCreate",
    "AlertUpdate",
    "AlertResponse",
    "PriceHistoryResponse",
    "PriceHistorySummary",
    "CrawlLogResponse",
]
