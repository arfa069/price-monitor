"""Debug script to find correct Taobao price selectors."""
import asyncio
import os
from playwright.async_api import async_playwright


async def test_selectors():
    url = "https://detail.tmall.com/item.htm?id=1016778217561"
    cdp_url = os.getenv("CDP_URL", "http://127.0.0.1:9222")

    async with async_playwright() as p:
        try:
            # Try CDP mode first (for logged-in sessions)
            print("Trying CDP mode...")
            browser = await p.chromium.connect_over_cdp(cdp_url)
            contexts = browser.contexts
            if contexts:
                context = contexts[0]
            else:
                context = await browser.new_context()
            page = await context.new_page()
            mode = "CDP"
        except Exception as e:
            print(f"CDP failed ({e}), trying headless mode...")
            # Fallback to headless
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            )
            page = await context.new_page()
            mode = "headless"

        print(f"Using mode: {mode}\n")

        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(15000)  # Wait longer for JS to render

        # Check page title to verify page loaded
        title = await page.title()
        print(f"Page title: {title}\n")

        # Get full HTML snippet to see structure
        html = await page.content()
        print(f"HTML length: {len(html)} chars\n")

        # Try various selectors and print results
        test_selectors = [
            # Common price selectors
            ".price-value",
            ".tm-price-panel .tm-price",
            "[data-price]",
            ".originPrice",
            "#J_PromoPrice .price-value",
            ".price-panel .price",
            ".tm-price",
            # More specific
            ".price",
            ".current-price",
            "[class*='price']",
            # New selectors from debugging
            ".priceWrap",
            "[class*='priceWrap']",
            ".price--",
            "[class*='price--']",
            # Original price
            "[class*='origin']",
            "[class*='original']",
            # Special for Tmall
            ". tm-pricePanel",
            "#J_StrPrice",
            # XPath
            "//*[contains(@class, 'price')]",
        ]

        print("=== Testing price selectors ===\n")

        for selector in test_selectors:
            try:
                if selector.startswith("//"):
                    elements = await page.locator(f"xpath={selector}").all()
                else:
                    elements = await page.locator(selector).all()

                if elements:
                    print(f"[OK] Selector: {selector}")
                    for i, el in enumerate(elements[:3]):  # Show first 3
                        text = await el.text_content()
                        tag = await el.evaluate("el => el.tagName")
                        cls = await el.evaluate("el => el.className")
                        print(f"  [{i}] <{tag}> class='{cls[:50]}...' text='{text[:30] if text else 'empty'}'")
                    print()
            except Exception as e:
                print(f"[FAIL] Selector: {selector} - Error: {e}\n")

        # Try to find SKU-related price changes
        print("\n=== Extracting price values ===\n")

        try:
            # Find priceWrap elements
            price_wraps = await page.locator("[class*='priceWrap']").all()
            for i, el in enumerate(price_wraps):
                print(f"PriceWrap {i}:")
                # Get inner HTML to see structure
                inner_html = await el.inner_html()
                print(f"  HTML snippet: {inner_html[:200]}...")
                # Get all text
                text = await el.text_content()
                print(f"  Full text: {text}")

                # Try to find price values inside
                prices = await el.locator("[class*='price']").all()
                for p in prices:
                    ptext = await p.text_content()
                    print(f"    Nested price: {ptext}")
                print()
        except Exception as e:
            print(f"Error: {e}")

        print("\n=== Looking for SKU/attribute selectors ===\n")

        # Check for selected SKU info
        try:
            # Find SKU selected items
            selected = await page.locator("[class*='selected'], [class*='selectedSku']").all()
            if selected:
                print("Selected SKU elements found:")
                for el in selected[:2]:
                    text = await el.text_content()
                    print(f"  - {text[:50]}")
        except:
            pass

        # Check for price display near main product info
        try:
            # Look for main price area
            main_price = await page.locator(".product-info, .product-detail, #J_DetailMeta").all()
            if main_price:
                print("\n[OK] Found main product info container")
                # Look for price within it
                price_in_main = await main_price[0].locator("[class*='price']").all()
                for el in price_in_main[:3]:
                    text = await el.text_content()
                    print(f"  Price element: '{text[:30]}'")
        except:
            pass

        await browser.close()


if __name__ == "__main__":
    asyncio.run(test_selectors())
