"""JavaScript deep-scan price extraction strategy."""
from typing import Any

from app.platforms.strategies.base import PriceExtractionStrategy


class JSDeeScanStrategy(PriceExtractionStrategy):
    """Price extraction using JavaScript evaluation to scan DOM and scripts.

    This strategy uses page.evaluate() to:
    1. Scan all price-class elements in the DOM
    2. Search inline scripts for price data (jdPrice, skuPrice, etc.)
    3. Check data-price attributes

    Useful for platforms like JD where price data is embedded in scripts
    or uses custom fonts for anti-scraping.
    """

    def __init__(self, currency: str = "CNY"):
        """Initialize with currency code.

        Args:
            currency: Currency code (default: CNY).
        """
        self.currency = currency

    async def extract(self, page) -> dict[str, Any]:
        """Run JavaScript to extract price from page.

        Args:
            page: Playwright page object.

        Returns:
            Dict with success, price, currency, and method keys.
        """
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
                return {
                    "success": True,
                    "price": result["price"],
                    "currency": self.currency,
                    "method": "js_deep_scan",
                }

            return {"success": False, "error": "Price not found via JS deep scan"}

        except Exception as e:
            return {"success": False, "error": str(e)}
