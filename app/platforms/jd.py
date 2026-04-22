"""JD platform adapter."""
from typing import Dict, Any
from app.platforms.base import BasePlatformAdapter


class JDAdapter(BasePlatformAdapter):
    """Adapter for JD.com price crawling."""

    async def extract_price(self, page) -> Dict[str, Any]:
        """Extract price from JD page."""
        try:
            price_selectors = [
                ".price .JD-price",
                ".p-price .price",
                "[data-price]",
                "#jdPrice .price",
                ".search_price",
            ]

            price = None
            for selector in price_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        price_text = await element.text_content()
                        if price_text:
                            price = float("".join(filter(lambda x: x in "0123456789.", price_text)))
                            if price > 0:
                                break
                except Exception:
                    continue

            if price is None:
                return {"success": False, "error": "Price not found"}

            return {"success": True, "price": price, "currency": "CNY"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def extract_title(self, page) -> str:
        """Extract title from JD page."""
        try:
            title_selectors = [
                ".sku-name",
                ".product-title",
                "h1.title",
                "#product-title",
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

            return await page.title()

        except Exception:
            return ""