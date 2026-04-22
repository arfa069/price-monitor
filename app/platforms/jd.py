"""JD platform adapter."""
from typing import Dict, Any
from app.platforms.base import BasePlatformAdapter
from app.config import settings


class JDAdapter(BasePlatformAdapter):
    """Adapter for JD.com price crawling.

    Supports two modes:
    1. CDP mode (recommended): Connects to an existing browser with JD login.
       Requires Edge/Chrome started with --remote-debugging-port=9222.
    2. Cookie mode: Launches headless browser and injects JD cookies.
       Set JD_COOKIE env var with the full cookie string.
    """

    async def _init_browser(self):
        """Initialize browser with JD cookies if using launch mode."""
        await super()._init_browser()

        # In launch mode (not CDP), inject cookies after browser init
        if not self._cdp_mode and settings.jd_cookie and self._context:
            cookies = self._parse_cookie_string(settings.jd_cookie)
            if cookies:
                await self._context.add_cookies(cookies)
                # Re-create page after adding cookies
                if self._page:
                    await self._page.close()
                self._page = await self._context.new_page()

    @staticmethod
    def _parse_cookie_string(cookie_str: str) -> list[dict]:
        """Parse cookie string 'key1=val1; key2=val2' into Playwright cookie format."""
        cookies = []
        for pair in cookie_str.split(";"):
            pair = pair.strip()
            if "=" not in pair:
                continue
            name, value = pair.split("=", 1)
            name = name.strip()
            value = value.strip()
            if name:
                cookies.append({
                    "name": name,
                    "value": value,
                    "domain": ".jd.com",
                    "path": "/",
                })
        return cookies

    async def extract_price(self, page) -> Dict[str, Any]:
        """Extract price from JD page using multiple strategies.

        Strategy 1: Direct text from known price selectors.
        Strategy 2: JavaScript deep scan of price elements and script content.
        Strategy 3: Font anti-scraping character analysis (for pages with custom fonts).
        """
        try:
            price = None

            # Strategy 1: Direct CSS selectors (most reliable when logged in)
            price_selectors = [
                ".product-price",       # Desktop product page (most common)
                ".p-price .price",      # Desktop alternative
                ".price .JD-price",     # Desktop alternative
                "[data-price]",         # Data attribute
                "#jdPrice .price",      # Price section
                ".p-price",             # Generic price container
                ".price",               # Generic price class
            ]

            for selector in price_selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        text = await element.text_content()
                        if text:
                            cleaned = text.replace("¥", "").replace("￥", "").replace(",", "").replace("$", "").strip()
                            # Skip if font anti-scraping detected (? chars)
                            if "?" in cleaned or "？" in cleaned:
                                continue
                            try:
                                val = float("".join(c for c in cleaned if c in "0123456789."))
                                if val > 0:
                                    price = val
                                    break
                            except ValueError:
                                continue
                except Exception:
                    continue

            # Strategy 2: JavaScript deep scan
            if price is None:
                try:
                    result = await page.evaluate(r'''() => {
                        const results = {price: null, methods: []};

                        // Scan all price-class elements
                        const priceEls = document.querySelectorAll(
                            '[class*="price"], [class*="Price"], [data-price]'
                        );
                        for (const el of priceEls) {
                            const text = el.textContent.trim();
                            if (!text) continue;
                            const hasAnti = text.includes('?') || text.includes('\uff1f');
                            if (!hasAnti) {
                                const cleaned = text.replace(/[\u00a5\uff04$,]/g, '').trim();
                                const num = parseFloat(cleaned);
                                if (!isNaN(num) && num > 0 && !results.price) {
                                    results.price = num;
                                    results.methods.push('js_element');
                                }
                            }
                        }

                        // Search inline scripts for price data
                        // Collect all matches, then pick the best one by priority
                        const scriptPrices = {};
                        const scripts = document.querySelectorAll('script');
                        for (const s of scripts) {
                            const t = s.textContent;
                            const patterns = [
                                [/"jdPrice"\s*:\s*["']?(\d+\.?\d*)/i, 'jdPrice'],
                                [/'jdPrice'\s*:\s*["']?(\d+\.?\d*)/i, 'jdPrice'],
                                [/"skuPrice"\s*:\s*["']?(\d+\.?\d*)/i, 'skuPrice'],
                                [/'skuPrice'\s*:\s*["']?(\d+\.?\d*)/i, 'skuPrice'],
                                [/\bprice\s*[:=]\s*["']?(\d+\.?\d*)/i, 'price'],
                            ];
                            for (const [pat, label] of patterns) {
                                const m = pat.exec(t);
                                if (m && !(label in scriptPrices)) {
                                    scriptPrices[label] = parseFloat(m[1]);
                                    results.methods.push('script_' + label + ': ' + m[1]);
                                }
                            }
                        }
                        // Priority: jdPrice > skuPrice > price
                        if (!results.price) {
                            for (const key of ['jdPrice', 'skuPrice', 'price']) {
                                if (key in scriptPrices && scriptPrices[key] > 0) {
                                    results.price = scriptPrices[key];
                                    break;
                                }
                            }
                        }

                        // data-price attribute
                        const dpEl = document.querySelector('[data-price]');
                        if (dpEl) {
                            const dpVal = parseFloat(dpEl.getAttribute('data-price'));
                            if (!isNaN(dpVal) && dpVal > 0 && !results.price) {
                                results.price = dpVal;
                            }
                            results.methods.push('data_price: ' + dpEl.getAttribute('data-price'));
                        }

                        return results;
                    }''')

                    if result.get("price"):
                        price = result["price"]

                except Exception:
                    pass

            if price is not None:
                return {"success": True, "price": price, "currency": "CNY"}

            return {"success": False, "error": "Price not found on page"}

        except Exception as e:
            return {"success": False, "error": str(e)}

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