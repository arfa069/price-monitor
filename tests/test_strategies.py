"""Tests for price extraction strategies."""

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

    def test_extract_returns_dict_structure(self):
        """extract() returns dict with success, price, currency, method keys."""
        from app.platforms.strategies.base import PriceExtractionStrategy

        class ConcreteStrategy(PriceExtractionStrategy):
            async def extract(self, page):
                return {"success": True, "price": 99.99, "currency": "CNY", "method": "test"}

        import asyncio
        strategy = ConcreteStrategy()
        mock_page = object()
        result = asyncio.get_event_loop().run_until_complete(strategy.extract(mock_page))

        assert "success" in result
        assert "price" in result
        assert "currency" in result
        assert "method" in result
        assert isinstance(result["price"], float)
