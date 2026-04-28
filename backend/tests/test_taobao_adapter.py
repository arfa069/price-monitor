"""Tests for TaobaoAdapter config wiring."""
from unittest.mock import patch


class TestTaobaoAdapterConfigWiring:
    """Tests that TaobaoAdapter correctly uses config settings."""

    def test_taobao_adapter_uses_taobao_js_deep_scan_enabled_from_settings(self):
        """TaobaoAdapter should read js_deep_scan setting from config."""
        from app.platforms.taobao import TaobaoAdapter

        # Mock settings with js_deep_scan_enabled = True
        with patch('app.platforms.taobao.settings') as mock_settings:
            mock_settings.taobao_js_deep_scan_enabled = True
            adapter = TaobaoAdapter()
            assert adapter.js_deep_scan_enabled is True
            assert adapter.js_strategy is not None

    def test_taobao_adapter_js_strategy_none_when_disabled(self):
        """TaobaoAdapter should have None js_strategy when disabled in config."""
        from app.platforms.taobao import TaobaoAdapter

        # Mock settings with js_deep_scan_enabled = False
        with patch('app.platforms.taobao.settings') as mock_settings:
            mock_settings.taobao_js_deep_scan_enabled = False
            adapter = TaobaoAdapter()
            assert adapter.js_deep_scan_enabled is False
            assert adapter.js_strategy is None

    def test_taobao_adapter_default_js_strategy_enabled(self):
        """TaobaoAdapter should have js_strategy when taobao_js_deep_scan_enabled is True by default."""
        from app.platforms.taobao import TaobaoAdapter

        # Mock settings with default taobao_js_deep_scan_enabled = True
        with patch('app.platforms.taobao.settings') as mock_settings:
            mock_settings.taobao_js_deep_scan_enabled = True
            adapter = TaobaoAdapter()
            assert adapter.js_strategy is not None

    def test_taobao_adapter_js_strategy_disabled_by_default(self):
        """TaobaoAdapter should have js_strategy = None when taobao_js_deep_scan_enabled is False."""
        from app.platforms.taobao import TaobaoAdapter

        # Mock settings with default taobao_js_deep_scan_enabled = False
        with patch('app.platforms.taobao.settings') as mock_settings:
            mock_settings.taobao_js_deep_scan_enabled = False
            adapter = TaobaoAdapter()
            assert adapter.js_strategy is None
