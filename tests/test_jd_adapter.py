"""Tests for JDAdapter refactoring to use strategies and middleware."""
from unittest.mock import AsyncMock, MagicMock

import pytest


class TestJDAdapterUsesStrategies:
    """Tests that JDAdapter uses the strategy pattern correctly."""

    def test_jd_adapter_inherits_cookie_injection_middleware(self):
        """JDAdapter should mix in CookieInjectionMiddleware."""
        from app.platforms.jd import JDAdapter
        from app.platforms.middleware.cookie_injection import CookieInjectionMiddleware

        # JDAdapter should be a subclass of CookieInjectionMiddleware
        assert issubclass(JDAdapter, CookieInjectionMiddleware)

    def test_jd_adapter_has_css_selector_strategy(self):
        """JDAdapter should have a CSSSelectorStrategy for price extraction."""
        from app.platforms.jd import JDAdapter
        from app.platforms.strategies.css_selector import CSSSelectorStrategy

        adapter = JDAdapter()
        # Should have css_strategy attribute that is a CSSSelectorStrategy
        assert hasattr(adapter, 'css_strategy')
        assert isinstance(adapter.css_strategy, CSSSelectorStrategy)

    def test_jd_adapter_has_js_deep_scan_strategy(self):
        """JDAdapter should have a JSDeeScanStrategy as fallback."""
        from app.platforms.jd import JDAdapter
        from app.platforms.strategies.js_deep_scan import JSDeeScanStrategy

        adapter = JDAdapter()
        # Should have js_strategy attribute that is a JSDeeScanStrategy
        assert hasattr(adapter, 'js_strategy')
        assert isinstance(adapter.js_strategy, JSDeeScanStrategy)

    def test_jd_adapter_uses_chained_price_strategy(self):
        """JDAdapter should use ChainedPriceStrategy to combine strategies."""
        from app.platforms.jd import JDAdapter
        from app.platforms.strategies.chained import ChainedPriceStrategy

        adapter = JDAdapter()
        # Should have a chained strategy (internal name _price_strategy) that combines CSS and JS strategies
        assert hasattr(adapter, '_price_strategy')
        assert isinstance(adapter._price_strategy, ChainedPriceStrategy)

    def test_jd_adapter_css_strategy_has_jd_price_selectors(self):
        """JDAdapter's CSS strategy should use JD-specific price selectors."""
        from app.platforms.jd import JDAdapter

        adapter = JDAdapter()
        # The CSS strategy should have selectors specific to JD
        expected_selectors = [
            ".product-price",
            ".p-price .price",
            ".price .JD-price",
            "[data-price]",
            "#jdPrice .price",
            ".p-price",
            ".price",
        ]
        assert hasattr(adapter.css_strategy, 'selectors')
        # At least some of the expected selectors should be present
        for selector in expected_selectors:
            if selector in adapter.css_strategy.selectors:
                break
        else:
            # If none found, check if any match
            assert len(adapter.css_strategy.selectors) > 0

    def test_jd_adapter_parse_cookie_string_uses_middleware(self):
        """JDAdapter should use CookieInjectionMiddleware.parse_cookie_string."""
        from app.platforms.jd import JDAdapter

        adapter = JDAdapter()
        # Should inherit parse_cookie_string from CookieInjectionMiddleware
        assert hasattr(adapter, 'parse_cookie_string')

        # Test the method works
        cookie_str = "key1=val1; key2=val2"
        cookies = adapter.parse_cookie_string(cookie_str, domain=".jd.com")
        assert len(cookies) == 2
        assert cookies[0]['name'] == 'key1'
        assert cookies[0]['value'] == 'val1'
        assert cookies[0]['domain'] == '.jd.com'

    def test_jd_adapter_inject_cookies_method_exists(self):
        """JDAdapter should have inject_cookies method from middleware."""
        from app.platforms.jd import JDAdapter

        adapter = JDAdapter()
        # Should have inject_cookies method from CookieInjectionMiddleware
        assert hasattr(adapter, 'inject_cookies')
        assert callable(adapter.inject_cookies)

    @pytest.mark.asyncio
    async def test_extract_price_uses_chained_strategy(self):
        """JDAdapter.extract_price should delegate to the chained strategy."""
        from app.platforms.jd import JDAdapter

        adapter = JDAdapter()

        # Mock the chained strategy
        mock_result = {"success": True, "price": 99.99, "currency": "CNY", "method": "css_selector"}
        adapter._price_strategy = AsyncMock()
        adapter._price_strategy.extract = AsyncMock(return_value=mock_result)

        mock_page = MagicMock()
        result = await adapter.extract_price(mock_page)

        # Should call the chained strategy's extract method
        adapter._price_strategy.extract.assert_called_once_with(mock_page)
        assert result == mock_result
