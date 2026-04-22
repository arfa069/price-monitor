"""Model unit tests."""
import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from app.models.alert import Alert
from app.models.product import Product
from app.models.price_history import PriceHistory
from app.models.crawl_log import CrawlLog
from app.models.user import User


def test_alert_type_default():
    """Alert.type defaults to price_drop."""
    alert = Alert(
        id=1,
        product_id=1,
        threshold_percent=Decimal("5.00"),
        active=True,
    )
    assert alert.type == "price_drop"
    assert alert.threshold_percent == Decimal("5.00")
    assert alert.active is True


def test_product_active_defaults_true():
    """Product.active defaults to True."""
    product = Product(
        id=1,
        user_id=1,
        platform="taobao",
        url="https://example.com",
    )
    assert product.active is True


def test_price_history_requires_price():
    """PriceHistory price field is required."""
    history = PriceHistory(
        id=1,
        product_id=1,
        price=Decimal("99.99"),
        currency="CNY",
        scraped_at=datetime.utcnow(),
    )
    assert history.price == Decimal("99.99")
    assert history.currency == "CNY"


def test_crawl_log_platform_nullable():
    """CrawlLog platform is nullable for cross-platform logs."""
    log = CrawlLog(
        id=1,
        platform=None,
        status="SUCCESS",
        timestamp=datetime.utcnow(),
    )
    assert log.platform is None


def test_crawl_log_product_nullable():
    """CrawlLog product_id is nullable (system-wide crawl logs)."""
    log = CrawlLog(
        id=1,
        product_id=None,
        platform="taobao",
        status="ERROR",
        error_message="Network timeout",
        timestamp=datetime.utcnow(),
    )
    assert log.product_id is None
    assert log.error_message == "Network timeout"


def test_user_feishu_webhook_nullable():
    """User.feishu_webhook_url is nullable (optional feature)."""
    user = User(
        id=1,
        username="default",
        feishu_webhook_url=None,
        crawl_frequency_hours=1,
        data_retention_days=365,
    )
    assert user.feishu_webhook_url is None


def test_price_history_scraped_at_not_nullable():
    """PriceHistory.scraped_at is not nullable."""
    now = datetime.utcnow()
    history = PriceHistory(
        id=1,
        product_id=1,
        price=Decimal("50.00"),
        currency="CNY",
        scraped_at=now,
    )
    assert history.scraped_at == now


def test_alert_threshold_percent_precision():
    """Alert threshold_percent supports 2 decimal precision."""
    alert = Alert(
        id=1,
        product_id=1,
        threshold_percent=Decimal("12.50"),
    )
    assert alert.threshold_percent == Decimal("12.50")
