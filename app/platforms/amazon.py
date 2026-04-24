"""Amazon platform adapter."""
from typing import Any

from app.platforms.base import BasePlatformAdapter


class AmazonAdapter(BasePlatformAdapter):
    """Adapter for Amazon price crawling."""

    async def extract_price(self, page) -> dict[str, Any]:
        """Extract price from Amazon page."""
        try:
            price_selectors = [
                ".a-price .a-offscreen",
                "#priceblock_ourprice",
                "#priceblock_dealprice",
                ".apexPriceToPay .a-offscreen",
                "#corePrice_feature_div .a-offscreen",
            ]

            price = None
            currency = "USD"

            for selector in price_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        price_text = await element.text_content()
                        if price_text:
                            # Handle different currency formats
                            price_str = price_text.replace("$", "").replace("¥", "").replace(",", "")
                            price = float("".join(filter(lambda x: x in "0123456789.", price_str)))
                            if price > 0:
                                if "¥" in price_text:
                                    currency = "CNY"
                                else:
                                    currency = "USD"
                                break
                except Exception:
                    continue

            if price is None:
                return {"success": False, "error": "Price not found"}

            return {"success": True, "price": price, "currency": currency}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def extract_title(self, page) -> str:
        """Extract title from Amazon page."""
        try:
            title_selectors = [
                "#productTitle",
                "#title",
                ".product-title-word-break",
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
