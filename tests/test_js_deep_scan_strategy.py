"""Tests for JSDeeScanStrategy."""


class TestJSDeeScanStrategy:
    """Tests for JSDeeScanStrategy."""

    def test_js_deep_scan_strategy_instantiable(self):
        """JSDeeScanStrategy can be instantiated."""
        from app.platforms.strategies.js_deep_scan import JSDeeScanStrategy

        strategy = JSDeeScanStrategy()
        assert strategy is not None

    def test_js_deep_scan_has_extract_method(self):
        """JSDeeScanStrategy has async extract method."""
        from app.platforms.strategies.js_deep_scan import JSDeeScanStrategy

        strategy = JSDeeScanStrategy()
        assert hasattr(strategy, 'extract')
        assert callable(strategy.extract)
