"""JD platform adapter."""
from typing import Any

from app.config import settings
from app.platforms.base import BasePlatformAdapter
from app.platforms.middleware.cookie_injection import CookieInjectionMiddleware
from app.platforms.strategies import (
    ChainedPriceStrategy,
    CSSSelectorStrategy,
    JSDeeScanStrategy,
)


class JDAdapter(BasePlatformAdapter, CookieInjectionMiddleware):
    """Adapter for JD.com price crawling.

    Supports two modes:
    1. CDP mode (recommended): Connects to an existing browser with JD login.
       Requires Edge/Chrome started with --remote-debugging-port=9222.
    2. Cookie mode: Launches headless browser and injects JD cookies.
       Set JD_COOKIE env var with the full cookie string.

    Uses ChainedPriceStrategy with:
    - CSSSelectorStrategy as primary extraction
    - JSDeeScanStrategy as fallback
    """

    def __init__(self):
        """Initialize JD adapter with strategies."""
        super().__init__()

        # CSS Selector strategy for direct price elements
        self.css_strategy = CSSSelectorStrategy(
            selectors=[
                ".product-price",       # Desktop product page (most common)
                ".p-price .price",      # Desktop alternative
                ".price .JD-price",     # Desktop alternative
                "[data-price]",         # Data attribute
                "#jdPrice .price",      # Price section
                ".p-price",             # Generic price container
                ".price",               # Generic price class
            ],
            currency="CNY",
        )

        # JavaScript deep scan strategy as fallback
        self.js_strategy = JSDeeScanStrategy(currency="CNY")

        # Chain CSS as primary, JS as fallback
        self._price_strategy = ChainedPriceStrategy([
            self.css_strategy,
            self.js_strategy,
        ])

    async def _init_browser(self):
        """Initialize browser with JD cookies if using launch mode."""
        await super()._init_browser()

        # In launch mode (not CDP), inject cookies after browser init
        if not self._cdp_mode and settings.jd_cookie and self._context:
            await self.inject_cookies(self._context, settings.jd_cookie, domain=".jd.com")
            # Re-create page after adding cookies
            if self._page:
                await self._page.close()
            self._page = await self._context.new_page()

    async def extract_price(self, page) -> dict[str, Any]:
        """Extract price from JD page using chained strategies.

        Uses CSSSelectorStrategy as primary, JSDeeScanStrategy as fallback.
        """
        return await self._price_strategy.extract(page)

    async def extract_title(self, page) -> str:
        """Extract title from JD page."""
        try:
            title_selectors = [
                ".sku-name",          # Desktop product title
                ".product-name",
                ".itemInfo-bar h1",
                "h1.title",
                "#product-title",
                ".p-sku-title",
                ".detail-title",
            ]

            for selector in title_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        title = await element.text_content()
                        if title and title.strip():
                            return title.strip()
                except Exception:
                    continue

            # Fallback to page title, strip JD suffix
            page_title = await page.title()
            if " - " in page_title:
                return page_title.split(" - ")[0].strip()
            if "【" in page_title:
                return page_title.split("【")[0].strip()
            return page_title.strip()

        except Exception:
            return ""

