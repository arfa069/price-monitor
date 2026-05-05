"""Pydantic schemas."""
from app.schemas.alert import AlertCreate, AlertResponse, AlertUpdate
from app.schemas.auth import MessageResponse, TokenResponse, UserLogin, UserRegister, UserResponse
from app.schemas.crawl_log import CrawlLogResponse
from app.schemas.job_match import (
    MatchAnalyzeRequest,
    MatchAnalyzeResponse,
    MatchResultListResponse,
    MatchResultResponse,
    UserResumeCreate,
    UserResumeResponse,
    UserResumeUpdate,
)
from app.schemas.price_history import PriceHistoryResponse, PriceHistorySummary
from app.schemas.product import (
    ProductCreate,
    ProductDetail,
    ProductResponse,
    ProductUpdate,
)
from app.schemas.user import UserConfigCreate, UserConfigResponse, UserConfigUpdate

__all__ = [
    "AlertCreate",
    "AlertUpdate",
    "AlertResponse",
    "CrawlLogResponse",
    "MatchAnalyzeRequest",
    "MatchAnalyzeResponse",
    "MatchResultResponse",
    "MatchResultListResponse",
    "PriceHistoryResponse",
    "PriceHistorySummary",
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    "ProductDetail",
    "UserConfigCreate",
    "UserConfigUpdate",
    "UserConfigResponse",
    "UserResumeCreate",
    "UserResumeUpdate",
    "UserResumeResponse",
    "UserLogin",
    "UserRegister",
    "UserResponse",
    "TokenResponse",
    "MessageResponse",
]
