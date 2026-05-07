"""Database models."""
from app.models.alert import Alert
from app.models.base import Base
from app.models.crawl_log import CrawlLog
from app.models.job_match import MatchResult, UserResume
from app.models.permission import Permission
from app.models.price_history import PriceHistory
from app.models.product import Product, ProductPlatformCron
from app.models.role import Role, role_permissions
from app.models.user import User

__all__ = [
    "Base",
    "User",
    "Product",
    "ProductPlatformCron",
    "PriceHistory",
    "Alert",
    "CrawlLog",
    "UserResume",
    "MatchResult",
    "Role",
    "Permission",
    "role_permissions",
]
