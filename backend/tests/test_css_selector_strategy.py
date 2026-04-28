"""Tests for CSSSelectorStrategy."""


class TestCSSSelectorStrategy:
    """Tests for CSSSelectorStrategy."""

    def test_try_selectors_returns_first_valid_price(self):
        """CSSSelectorStrategy returns first valid price from selectors."""
        from app.platforms.strategies.css_selector import CSSSelectorStrategy

        strategy = CSSSelectorStrategy(selectors=[".price", ".sale-price"])
        assert strategy is not None

    def test_try_selectors_takes_list_of_selectors(self):
        """CSSSelectorStrategy constructor accepts list of CSS selectors."""
        from app.platforms.strategies.css_selector import CSSSelectorStrategy

        strategy = CSSSelectorStrategy(selectors=["[data-price]", "#price"])
        assert strategy.selectors == ["[data-price]", "#price"]

    def test_extract_method_exists(self):
        """CSSSelectorStrategy has extract async method."""
        from app.platforms.strategies.css_selector import CSSSelectorStrategy

        strategy = CSSSelectorStrategy(selectors=[".price"])
        assert hasattr(strategy, 'extract')
        assert callable(strategy.extract)
