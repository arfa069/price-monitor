"""Tests for price extraction strategies."""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestPriceExtractionStrategyBase:
    """Tests for PriceExtractionStrategy base class."""

    def test_base_is_abstract(self):
        """PriceExtractionStrategy cannot be instantiated directly."""
        from app.platforms.strategies.base import PriceExtractionStrategy

        # Should not be able to instantiate directly
        with pytest.raises(TypeError):
            PriceExtractionStrategy()

    def test_concrete_implementation_required_extract_method(self):
        """Concrete strategy must implement extract method."""
        from app.platforms.strategies.base import PriceExtractionStrategy

        class IncompleteStrategy(PriceExtractionStrategy):
            pass

        with pytest.raises(TypeError):
            IncompleteStrategy()

    def test_concrete_implementation_with_extract_is_valid(self):
        """Concrete strategy with extract method can be instantiated."""
        from app.platforms.strategies.base import PriceExtractionStrategy

        class ConcreteStrategy(PriceExtractionStrategy):
            async def extract(self, page):
                return {"success": True, "price": 0.0, "currency": "CNY", "method": "test"}

        # Should instantiate without error
        strategy = ConcreteStrategy()
        assert strategy is not None

    @pytest.mark.asyncio
    async def test_extract_returns_dict_structure(self):
        """extract() returns dict with success, price, currency, method keys."""
        from app.platforms.strategies.base import PriceExtractionStrategy

        class ConcreteStrategy(PriceExtractionStrategy):
            async def extract(self, page):
                return {"success": True, "price": 99.99, "currency": "CNY", "method": "test"}

        strategy = ConcreteStrategy()
        mock_page = object()
        result = await strategy.extract(mock_page)

        assert "success" in result
        assert "price" in result
        assert "currency" in result
        assert "method" in result
        assert isinstance(result["price"], float)


class TestCSSSelectorStrategy:
    """Tests for CSSSelectorStrategy actual extraction logic."""

    @pytest.mark.asyncio
    async def test_extract_success_first_selector(self):
        """Returns price when first selector matches."""
        from app.platforms.strategies.css_selector import CSSSelectorStrategy

        strategy = CSSSelectorStrategy(selectors=[".price", "#price"])

        mock_element = AsyncMock()
        mock_element.count = AsyncMock(return_value=1)
        mock_element.text_content = AsyncMock(return_value="¥199.99")

        mock_locator = MagicMock()
        mock_locator.first = mock_element

        mock_page = MagicMock()
        mock_page.locator = MagicMock(return_value=mock_locator)

        result = await strategy.extract(mock_page)

        assert result["success"] is True
        assert result["price"] == 199.99
        assert result["currency"] == "CNY"
        assert result["method"] == "css_selector"

    @pytest.mark.asyncio
    async def test_extract_tries_next_selector(self):
        """Falls back to next selector if first fails."""
        from app.platforms.strategies.css_selector import CSSSelectorStrategy

        strategy = CSSSelectorStrategy(selectors=[".missing", "#price"])

        # First selector: no match
        missing_element = AsyncMock()
        missing_element.count = AsyncMock(return_value=0)

        # Second selector: match
        price_element = AsyncMock()
        price_element.count = AsyncMock(return_value=1)
        price_element.text_content = AsyncMock(return_value="¥299.00")

        def mock_locator(selector):
            if selector == ".missing":
                m = MagicMock()
                m.first = missing_element
                return m
            else:
                m = MagicMock()
                m.first = price_element
                return m

        mock_page = MagicMock()
        mock_page.locator = mock_locator

        result = await strategy.extract(mock_page)

        assert result["success"] is True
        assert result["price"] == 299.0

    @pytest.mark.asyncio
    async def test_extract_skips_anti_scraping(self):
        """Skips prices with anti-scraping characters."""
        from app.platforms.strategies.css_selector import CSSSelectorStrategy

        strategy = CSSSelectorStrategy(selectors=[".price"])

        mock_element = AsyncMock()
        mock_element.count = AsyncMock(return_value=1)
        mock_element.text_content = AsyncMock(return_value="¥?99")

        mock_locator = MagicMock()
        mock_locator.first = mock_element

        mock_page = MagicMock()
        mock_page.locator = MagicMock(return_value=mock_locator)

        result = await strategy.extract(mock_page)

        assert result["success"] is False
        assert "not found" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_extract_no_match(self):
        """Returns failure when no selector matches."""
        from app.platforms.strategies.css_selector import CSSSelectorStrategy

        strategy = CSSSelectorStrategy(selectors=[".missing"])

        mock_element = AsyncMock()
        mock_element.count = AsyncMock(return_value=0)

        mock_locator = MagicMock()
        mock_locator.first = mock_element

        mock_page = MagicMock()
        mock_page.locator = MagicMock(return_value=mock_locator)

        result = await strategy.extract(mock_page)

        assert result["success"] is False
        assert "not found" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_extract_zero_price_rejected(self):
        """Zero price is rejected."""
        from app.platforms.strategies.css_selector import CSSSelectorStrategy

        strategy = CSSSelectorStrategy(selectors=[".price"])

        mock_element = AsyncMock()
        mock_element.count = AsyncMock(return_value=1)
        mock_element.text_content = AsyncMock(return_value="¥0.00")

        mock_locator = MagicMock()
        mock_locator.first = mock_element

        mock_page = MagicMock()
        mock_page.locator = MagicMock(return_value=mock_locator)

        result = await strategy.extract(mock_page)

        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_extract_custom_currency(self):
        """Custom currency is preserved."""
        from app.platforms.strategies.css_selector import CSSSelectorStrategy

        strategy = CSSSelectorStrategy(selectors=[".price"], currency="USD")

        mock_element = AsyncMock()
        mock_element.count = AsyncMock(return_value=1)
        mock_element.text_content = AsyncMock(return_value="$49.99")

        mock_locator = MagicMock()
        mock_locator.first = mock_element

        mock_page = MagicMock()
        mock_page.locator = MagicMock(return_value=mock_locator)

        result = await strategy.extract(mock_page)

        assert result["success"] is True
        assert result["currency"] == "USD"


class TestJSDeeScanStrategy:
    """Tests for JSDeeScanStrategy actual extraction logic."""

    @pytest.mark.asyncio
    async def test_extract_from_element(self):
        """Extracts price from DOM element."""
        from app.platforms.strategies.js_deep_scan import JSDeeScanStrategy

        strategy = JSDeeScanStrategy()

        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value={"price": 199.99, "methods": ["js_element"]})

        result = await strategy.extract(mock_page)

        assert result["success"] is True
        assert result["price"] == 199.99
        assert result["method"] == "js_deep_scan"

    @pytest.mark.asyncio
    async def test_extract_from_script(self):
        """Extracts price from inline script jdPrice."""
        from app.platforms.strategies.js_deep_scan import JSDeeScanStrategy

        strategy = JSDeeScanStrategy()

        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value={"price": None, "methods": ["script_jdPrice: 299.00"]})

        # Need to simulate script price resolution
        # The strategy doesn't return script price in the mock above, so let's
        # mock the evaluate to return a price found via script
        mock_page.evaluate = AsyncMock(
            return_value={"price": 299.00, "methods": ["script_jdPrice: 299.00"]}
        )

        result = await strategy.extract(mock_page)

        assert result["success"] is True
        assert result["price"] == 299.00

    @pytest.mark.asyncio
    async def test_extract_not_found(self):
        """Returns failure when no price found."""
        from app.platforms.strategies.js_deep_scan import JSDeeScanStrategy

        strategy = JSDeeScanStrategy()

        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value={"price": None, "methods": []})

        result = await strategy.extract(mock_page)

        assert result["success"] is False
        assert "not found" in result.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_extract_exception_handled(self):
        """JavaScript exceptions are caught and returned."""
        from app.platforms.strategies.js_deep_scan import JSDeeScanStrategy

        strategy = JSDeeScanStrategy()

        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(side_effect=Exception("page crashed"))

        result = await strategy.extract(mock_page)

        assert result["success"] is False
        assert "page crashed" in result.get("error", "")

    @pytest.mark.asyncio
    async def test_extract_custom_currency(self):
        """Custom currency is preserved."""
        from app.platforms.strategies.js_deep_scan import JSDeeScanStrategy

        strategy = JSDeeScanStrategy(currency="USD")

        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value={"price": 99.99, "methods": ["js_element"]})

        result = await strategy.extract(mock_page)

        assert result["success"] is True
        assert result["currency"] == "USD"
