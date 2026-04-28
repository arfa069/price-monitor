"""Base platform adapter for price crawling."""
import asyncio
import random
from abc import ABC, abstractmethod
from typing import Any

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.config import settings


class BasePlatformAdapter(ABC):
    """Abstract base class for platform-specific crawlers.

    Supports two browser modes:
    1. **Launch mode** (default): Launches a headless Chromium instance.
    2. **CDP mode**: Connects to an existing browser via Chrome DevTools Protocol.
       This is useful for platforms that require login (e.g. JD) — you log in
       manually in the browser, then the adapter reuses that session.

    Browser instances are cached at class level to avoid launching multiple browsers.
    """

    # Class-level browser cache (shared across all instances of the same platform)
    _shared_playwright: Playwright | None = None
    _shared_browser: Browser | None = None
    _shared_context: BrowserContext | None = None
    _cdp_mode: bool = False

    def __init__(self):
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._cdp_mode: bool = False

    @classmethod
    async def _get_shared_browser(cls) -> tuple[Playwright, Browser, BrowserContext, bool]:
        """Get or create shared browser instance for this platform adapter class."""
        if cls._shared_playwright is not None:
            return cls._shared_playwright, cls._shared_browser, cls._shared_context, cls._cdp_mode

        playwright = await async_playwright().start()

        if settings.cdp_enabled and settings.cdp_url:
            browser = await playwright.chromium.connect_over_cdp(settings.cdp_url)
            cdp_mode = True
            contexts = browser.contexts
            if contexts:
                context = contexts[0]
            else:
                context = await browser.new_context()
        else:
            browser = await playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )
            cdp_mode = False
            context_options = {
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
            if settings.crawl_proxy_enabled and settings.crawl_proxy_url:
                context_options["proxy"] = {"url": settings.crawl_proxy_url}
            context = await browser.new_context(**context_options)

        cls._shared_playwright = playwright
        cls._shared_browser = browser
        cls._shared_context = context
        cls._cdp_mode = cdp_mode

        return playwright, browser, context, cdp_mode

    @classmethod
    async def _close_shared_browser(cls) -> None:
        """Close shared browser instance."""
        if cls._shared_context:
            await cls._shared_context.close()
            cls._shared_context = None
        if cls._shared_browser:
            await cls._shared_browser.close()
            cls._shared_browser = None
        if cls._shared_playwright:
            await cls._shared_playwright.stop()
            cls._shared_playwright = None
        cls._cdp_mode = False

    @classmethod
    async def _create_new_page(cls) -> Page:
        """Create a new page in the shared context."""
        _, _, context, _ = await cls._get_shared_browser()
        return await context.new_page()

    async def _init_browser(self):
        """Initialize browser — use shared instance for efficiency."""
        if self._playwright is not None:
            return

        self._playwright, self._browser, self._context, self._cdp_mode = await self._get_shared_browser()
        self._page = await self._context.new_page()

    async def _close_browser(self):
        """Clean up browser resources.

        Only close the page - keep the shared browser instance alive.
        """
        if self._page:
            await self._page.close()
            self._page = None

    @abstractmethod
    async def extract_price(self, page) -> dict[str, Any]:
        """Extract price from page. Must be implemented by subclasses."""
        pass

    @abstractmethod
    async def extract_title(self, page) -> str:
        """Extract title from page. Must be implemented by subclasses."""
        pass

    async def crawl(self, url: str) -> dict[str, Any]:
        """Crawl a product page and extract price and title.

        In CDP mode, reuses the existing browser page (with login session).
        In launch mode, creates a fresh browser instance.
        Overall operation timeout is 90s.
        """
        await self._init_browser()

        try:
            async with asyncio.timeout(90):
                # Use domcontentloaded + explicit price selector wait instead of
                # networkidle — networkidle stalls on JD due to ad trackers/WebSocket pings
                await self._page.goto(url, wait_until="domcontentloaded", timeout=45000)
                # Wait for price element to be attached (not necessarily visible) to handle lazy-loaded content
                await self._page.wait_for_selector(
                    "[class*='price'], [class*='Price'], .p-price, .product-price",
                    timeout=20000,
                    state="attached",
                )
                # Scroll to trigger lazy-loaded content on Taobao
                await self._page.evaluate("window.scrollBy(0, 300)")
                # Give more time for JS to render prices (especially Taobao with lazy loading)
                # Stay 8~12 seconds on each product page for full rendering
                await self._page.wait_for_timeout(random.uniform(8000, 12000))
                # Scroll back to top
                await self._page.evaluate("window.scrollTo(0, 0)")

                price_data = await self.extract_price(self._page)
                title = await self.extract_title(self._page)

                if price_data.get("success"):
                    return {
                        "success": True,
                        "price": price_data["price"],
                        "currency": price_data.get("currency", "CNY"),
                        "title": title,
                    }
                else:
                    return {
                        "success": False,
                        "error": price_data.get("error", "Failed to extract price"),
                    }

        except TimeoutError:
            return {
                "success": False,
                "error": "Crawl timeout: page took longer than 90s to respond",
            }
        except PlaywrightTimeoutError as e:
            return {
                "success": False,
                "error": f"Page load timeout: {e}",
            }
        except (ConnectionError, OSError) as e:
            return {
                "success": False,
                "error": f"Network error: {e}",
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {e}",
            }
        finally:
            await self._close_browser()
