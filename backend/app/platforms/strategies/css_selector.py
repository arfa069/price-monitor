"""CSS selector-based price extraction strategy."""
from typing import Any

from app.platforms.strategies.base import PriceExtractionStrategy


class CSSSelectorStrategy(PriceExtractionStrategy):
    """Price extraction using CSS selectors.

    Tries a list of CSS selectors in order, returns the first valid price found.
    Useful for platforms where price elements have predictable selectors.
    """

    def __init__(self, selectors: list[str], currency: str = "CNY"):
        """Initialize with list of CSS selectors to try.

        Args:
            selectors: List of CSS selector strings to try in order.
            currency: Currency code (default: CNY).
        """
        self.selectors = selectors
        self.currency = currency

    async def extract(self, page) -> dict[str, Any]:
        """Try each CSS selector and return first valid price.

        Args:
            page: Playwright page object.

        Returns:
            Dict with success, price, currency, and method keys.
        """
        for selector in self.selectors:
            try:
                element = page.locator(selector).first
                if await element.count() > 0:
                    text = await element.text_content()
                    if text:
                        # Clean price string - keep only digits and dots
                        cleaned = text.replace("¥", "").replace("￥", "").replace(",", "").replace("$", "").replace(" ", "").strip()
                        # Skip if anti-scraping characters detected
                        if "?" in cleaned or "？" in cleaned:
                            continue
                        try:
                            price = float("".join(c for c in cleaned if c in "0123456789."))
                            if price > 0:
                                return {
                                    "success": True,
                                    "price": price,
                                    "currency": self.currency,
                                    "method": "css_selector",
                                }
                        except ValueError:
                            continue
            except Exception:
                continue

        return {"success": False, "error": "Price not found"}
