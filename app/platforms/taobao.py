"""Taobao platform adapter."""
from typing import Any

from app.config import settings
from app.platforms.base import BasePlatformAdapter
from app.platforms.strategies import (
    CSSSelectorStrategy,
    JSDeeScanStrategy,
)


class TaobaoAdapter(BasePlatformAdapter):
    """Adapter for Taobao/Tmall price crawling.

    Uses CSSSelectorStrategy as primary extraction method.
    Uses JSDeeScanStrategy as fallback if taobao_js_deep_scan_enabled is set in config.
    """

    def __init__(self):
        """Initialize Taobao adapter with strategies.

        Reads taobao_js_deep_scan_enabled from config to determine if JS deep scan
        fallback should be enabled.
        """
        super().__init__()

        # Check config for JS deep scan setting
        self.js_deep_scan_enabled = settings.taobao_js_deep_scan_enabled

        # Primary strategy: CSS selector-based extraction
        self.css_strategy = CSSSelectorStrategy(
            selectors=[
                ".price-value",
                ".tm-price-panel .tm-price",
                "[data-price]",
                ".originPrice",
                "#J_PromoPrice .price-value",
            ],
            currency="CNY",
        )

        # Fallback strategy: JavaScript deep scan (only if enabled in config)
        self.js_strategy = JSDeeScanStrategy() if self.js_deep_scan_enabled else None

    async def extract_price(self, page) -> dict[str, Any]:
        """Extract price from Taobao page.

        Tries CSS selector strategy first, then JS deep scan as fallback.
        """
        # Try CSS selector strategy first
        result = await self.css_strategy.extract(page)
        if result.get("success"):
            return result

        # Fallback to JS deep scan if enabled and CSS failed
        if self.js_strategy:
            js_result = await self.js_strategy.extract(page)
            if js_result.get("success"):
                return js_result

        return {"success": False, "error": "Price not found on Taobao page"}

    async def extract_title(self, page) -> str:
        """Extract title from Taobao page."""
        try:
            title_selectors = [
                ".product-title",
                ".item-title",
                "h1.title",
                "#J_ItemInfo .title",
            ]

            for selector in title_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        title = await element.text_content()
                        if title:
                            return title.strip()
                except Exception:
                    continue

            # Fallback to page title
            return await page.title()

        except Exception:
            return ""
