"""Tests for Pydantic schema validation."""
from decimal import Decimal

import pytest
from pydantic import ValidationError


# --- Alert Schemas ---


class TestAlertCreate:
    def test_valid_alert_create(self):
        from app.schemas.alert import AlertCreate

        alert = AlertCreate(product_id=1, threshold_percent=Decimal("5.00"), active=True)
        assert alert.product_id == 1
        assert alert.threshold_percent == Decimal("5.00")
        assert alert.active is True

    def test_threshold_percent_out_of_range_high(self):
        from app.schemas.alert import AlertCreate

        with pytest.raises(ValidationError):
            AlertCreate(product_id=1, threshold_percent=Decimal("101.00"))

    def test_threshold_percent_out_of_range_low(self):
        from app.schemas.alert import AlertCreate

        with pytest.raises(ValidationError):
            AlertCreate(product_id=1, threshold_percent=Decimal("-1.00"))

    def test_defaults(self):
        from app.schemas.alert import AlertCreate

        alert = AlertCreate(product_id=1)
        assert alert.threshold_percent == Decimal("5.00")
        assert alert.active is True


class TestAlertUpdate:
    def test_partial_update(self):
        from app.schemas.alert import AlertUpdate

        alert = AlertUpdate(threshold_percent=Decimal("10.00"))
        assert alert.threshold_percent == Decimal("10.00")
        assert alert.active is None


# --- Auth Schemas ---


class TestUserRegister:
    def test_valid_registration(self):
        from app.schemas.auth import UserRegister

        user = UserRegister(username="testuser", email="test@example.com", password="secure123")
        assert user.username == "testuser"
        assert user.email == "test@example.com"

    def test_username_too_short(self):
        from app.schemas.auth import UserRegister

        with pytest.raises(ValidationError):
            UserRegister(username="ab", email="test@example.com", password="secure123")

    def test_username_invalid_characters(self):
        from app.schemas.auth import UserRegister

        with pytest.raises(ValidationError):
            UserRegister(username="test@user", email="test@example.com", password="secure123")

    def test_invalid_email(self):
        from app.schemas.auth import UserRegister

        with pytest.raises(ValidationError):
            UserRegister(username="testuser", email="not-an-email", password="secure123")

    def test_password_too_short(self):
        from app.schemas.auth import UserRegister

        with pytest.raises(ValidationError):
            UserRegister(username="testuser", email="test@example.com", password="12345")


class TestUserLogin:
    def test_valid_login(self):
        from app.schemas.auth import UserLogin

        login = UserLogin(username="testuser", password="secure123")
        assert login.username == "testuser"


# --- Product Schemas ---


class TestProductCreate:
    def test_valid_product(self):
        from app.schemas.product import ProductCreate

        product = ProductCreate(platform="jd", url="https://item.jd.com/123.html")
        assert product.platform == "jd"

    def test_invalid_platform(self):
        from app.schemas.product import ProductCreate

        with pytest.raises(ValidationError):
            ProductCreate(platform="unknown", url="https://example.com")

    def test_invalid_url_no_protocol(self):
        from app.schemas.product import ProductCreate

        with pytest.raises(ValidationError):
            ProductCreate(platform="taobao", url="example.com")

    def test_invalid_url_ftp(self):
        from app.schemas.product import ProductCreate

        with pytest.raises(ValidationError):
            ProductCreate(platform="taobao", url="ftp://example.com")

    def test_url_stripped(self):
        from app.schemas.product import ProductCreate

        product = ProductCreate(platform="amazon", url="  https://amazon.com/dp/B123  ")
        assert product.url == "https://amazon.com/dp/B123"


class TestProductUpdate:
    def test_empty_url_rejected(self):
        from app.schemas.product import ProductUpdate

        with pytest.raises(ValidationError):
            ProductUpdate(url="")

    def test_none_url_allowed(self):
        from app.schemas.product import ProductUpdate

        update = ProductUpdate(active=False)
        assert update.url is None


class TestProductBatchCreate:
    def test_too_many_items_rejected(self):
        from app.schemas.product import ProductBatchCreate, ProductBatchCreateItem

        items = [ProductBatchCreateItem(url=f"https://example.com/{i}") for i in range(101)]
        with pytest.raises(ValidationError):
            ProductBatchCreate(items=items)

    def test_max_items_accepted(self):
        from app.schemas.product import ProductBatchCreate, ProductBatchCreateItem

        items = [ProductBatchCreateItem(url=f"https://example.com/{i}") for i in range(100)]
        batch = ProductBatchCreate(items=items)
        assert len(batch.items) == 100


class TestProductPlatformCronCreate:
    def test_valid_platform(self):
        from app.schemas.product import ProductPlatformCronCreate

        config = ProductPlatformCronCreate(platform="taobao", cron_expression="0 9 * * *")
        assert config.platform == "taobao"

    def test_invalid_platform(self):
        from app.schemas.product import ProductPlatformCronCreate

        with pytest.raises(ValidationError):
            ProductPlatformCronCreate(platform="pdd")

    def test_cron_expression_too_long(self):
        from app.schemas.product import ProductPlatformCronCreate

        with pytest.raises(ValidationError):
            ProductPlatformCronCreate(platform="jd", cron_expression="x" * 101)
