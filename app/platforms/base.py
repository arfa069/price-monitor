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
    """

    def __init__(self):
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._page: Page | None = None
        self._cdp_mode: bool = False  # True if connected via CDP

    async def _init_browser(self):
        """Initialize browser — either via CDP connection or fresh launch."""
        if self._playwright is not None:
            return

        self._playwright = await async_playwright().start()

        if settings.cdp_enabled and settings.cdp_url:
            # CDP mode: connect to an existing browser session
            self._browser = await self._playwright.chromium.connect_over_cdp(settings.cdp_url)
            self._cdp_mode = True
            # Use the default context from the existing browser (it has cookies/login)
            contexts = self._browser.contexts
            if contexts:
                # Reuse the existing context (has login cookies) but always
                # create a new page to avoid interfering with user's tabs.
                self._context = contexts[0]
                self._page = await self._context.new_page()
            else:
                self._context = await self._browser.new_context()
                self._page = await self._context.new_page()
        else:
            # Launch mode: start a fresh headless browser
            self._cdp_mode = False
            self._browser = await self._playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )

            context_options = {
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
            if settings.crawl_proxy_enabled and settings.crawl_proxy_url:
                context_options["proxy"] = {"url": settings.crawl_proxy_url}

            self._context = await self._browser.new_context(**context_options)
            self._page = await self._context.new_page()

    async def _close_browser(self):
        """Clean up browser resources.

        In CDP mode, we only disconnect — the user's browser stays open.
        In launch mode, we close everything.
        """
        if self._cdp_mode:
            # CDP mode: close our page, disconnect from browser (don't close user's browser)
            if self._page:
                await self._page.close()
            if self._playwright:
                await self._playwright.stop()
            self._playwright = None
            self._browser = None
            self._context = None
            self._page = None
        else:
            # Launch mode: close everything we created
            if self._page:
                await self._page.close()
            if self._context:
                await self._context.close()
            if self._browser:
                await self._browser.close()
            if self._playwright:
                await self._playwright.stop()
            self._playwright = None
            self._browser = None
            self._context = None
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
                await self._page.wait_for_selector(
                    "[class*='price'], [class*='Price'], .p-price, .product-price",
                    timeout=20000,
                )
                # Give WebFont time to load so price characters render (JD uses custom font for anti-scraping)
                # Stay 4~6 seconds on each product page for full rendering
                await self._page.wait_for_timeout(random.uniform(4000, 6000))

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
