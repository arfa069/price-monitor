"""Base platform adapter for price crawling."""
from abc import ABC, abstractmethod
from typing import Dict, Any
import asyncio

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

from app.config import settings


class BasePlatformAdapter(ABC):
    """Abstract base class for platform-specific crawlers."""

    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    async def _init_browser(self):
        """Initialize Playwright browser."""
        if self.playwright is None:
            self.playwright = async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                ],
            )

            # Build context options including proxy if enabled
            context_options = {
                "viewport": {"width": 1920, "height": 1080},
                "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }

            # Apply proxy settings when enabled and URL is configured
            if settings.crawl_proxy_enabled and settings.crawl_proxy_url:
                context_options["proxy"] = {"url": settings.crawl_proxy_url}

            self.context = await self.browser.new_context(**context_options)
            self.page = await self.context.new_page()

    async def _close_browser(self):
        """Close Playwright browser."""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    @abstractmethod
    async def extract_price(self, page) -> Dict[str, Any]:
        """Extract price from page. Must be implemented by subclasses."""
        pass

    @abstractmethod
    async def extract_title(self, page) -> str:
        """Extract title from page. Must be implemented by subclasses."""
        pass

    async def crawl(self, url: str) -> Dict[str, Any]:
        """Crawl a product page and extract price and title.

        Overall operation timeout is 60s to prevent hanging on slow pages.
        """
        await self._init_browser()

        try:
            # Wrap entire crawl in an asyncio timeout (60s total)
            async with asyncio.timeout(60):
                await self.page.goto(url, wait_until="networkidle", timeout=30000)

                # Wait for dynamic content to load
                await self.page.wait_for_load_state("domcontentloaded")

                # Extract data
                price_data = await self.extract_price(self.page)
                title = await self.extract_title(self.page)

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

        except asyncio.TimeoutError:
            return {
                "success": False,
                "error": "Crawl timeout: page took longer than 60s to respond",
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
            # Catch-all for unexpected errors during extraction
            return {
                "success": False,
                "error": f"Unexpected error: {e}",
            }
        finally:
            await self._close_browser()