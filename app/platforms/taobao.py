"""Taobao platform adapter."""
from typing import Dict, Any
from app.platforms.base import BasePlatformAdapter


class TaobaoAdapter(BasePlatformAdapter):
    """Adapter for Taobao/Tmall price crawling."""

    async def extract_price(self, page) -> Dict[str, Any]:
        """Extract price from Taobao page."""
        try:
            # Try multiple selectors for Taobao price
            price_selectors = [
                ".price-value",
                ".tm-price-panel .tm-price",
                "[data-price]",
                ".originPrice",
                "#J_PromoPrice .price-value",
            ]

            price = None
            for selector in price_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        price_text = await element.text_content()
                        if price_text:
                            # Clean price string
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