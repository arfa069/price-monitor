"""End-to-end test: JD product crawl via API + direct adapter.

Usage:
    python scripts/test_jd_crawl.py                        # Default JD product
    python scripts/test_jd_crawl.py --url <jd_product_url>   # Custom URL

This script tests the full pipeline WITHOUT Celery:
1. Create product via API (HTTP POST /products)
2. Crawl price directly via JDAdapter (bypassing Celery)
3. Save price history to DB
4. Verify data via API (HTTP GET /products/{id}/history)
5. Create alert and test price drop notification
"""
import argparse
import asyncio
import sys
from datetime import datetime, timezone
from decimal import Decimal

# Add project root to path
sys.path.insert(0, ".")

from httpx import AsyncClient, ASGITransport
from app.main import app
from app.database import AsyncSessionLocal
from app.models.product import Product
from app.models.price_history import PriceHistory
from app.models.alert import Alert
from app.platforms.jd import JDAdapter


# Default JD product for testing (iPhone 16 Pro)
DEFAULT_JD_URL = "https://item.jd.com/100128525698.html"


async def create_product(client: AsyncClient, url: str) -> dict:
    """Step 1: Create product via API."""
    print(f"\n{'='*60}")
    print("Step 1: Creating product via API")
    print(f"{'='*60}")
    print(f"  URL: {url}")

    resp = await client.post(
        "/products",
        json={
            "platform": "jd",
            "url": url,
            "active": True,
        },
    )
    print(f"  Status: {resp.status_code}")
    print(f"  Response: {resp.json()}")
    return resp.json()


async def crawl_directly(url: str) -> dict:
    """Step 2: Crawl price directly using JDAdapter."""
    print(f"\n{'='*60}")
    print("Step 2: Crawling price via JDAdapter (direct, no Celery)")
    print(f"{'='*60}")

    adapter = JDAdapter()
    try:
        result = await adapter.crawl(url)
        print(f"  Result: {result}")
        return result
    except Exception as e:
        print(f"  ERROR: {e}")
        return {"success": False, "error": str(e)}


async def save_price_to_db(product_id: int, price: Decimal, currency: str) -> None:
    """Step 3: Save crawled price to DB directly."""
    print(f"\n{'='*60}")
    print("Step 3: Saving price to database")
    print(f"{'='*60}")
    print(f"  Product ID: {product_id}")
    print(f"  Price: {price} {currency}")

    async with AsyncSessionLocal() as db:
        history = PriceHistory(
            product_id=product_id,
            price=price,
            currency=currency,
            scraped_at=datetime.now(timezone.utc),
        )
        db.add(history)
        await db.commit()
        print(f"  Saved! History ID: {history.id}")


async def verify_product_detail(client: AsyncClient, product_id: int) -> dict:
    """Step 4: Verify product data via API."""
    print(f"\n{'='*60}")
    print("Step 4: Fetching product detail via API")
    print(f"{'='*60}")

    resp = await client.get(f"/products/{product_id}")
    print(f"  Status: {resp.status_code}")
    detail = resp.json()
    print(f"  Title: {detail.get('title', 'N/A')}")
    return detail


async def verify_price_history(client: AsyncClient, product_id: int) -> list:
    """Step 5: Verify price history via API."""
    print(f"\n{'='*60}")
    print("Step 5: Fetching price history via API")
    print(f"{'='*60}")

    resp = await client.get(f"/products/{product_id}/history")
    print(f"  Status: {resp.status_code}")
    history = resp.json()
    for entry in history:
        print(f"  Price: {entry['price']} {entry['currency']} @ {entry['scraped_at']}")
    return history


async def create_alert_and_test(
    client: AsyncClient, product_id: int, threshold_percent: Decimal
) -> dict:
    """Step 6: Create an alert and test notification trigger."""
    print(f"\n{'='*60}")
    print("Step 6: Creating price drop alert")
    print(f"{'='*60}")
    print(f"  Product ID: {product_id}")
    print(f"  Threshold: {threshold_percent}%")

    resp = await client.post(
        "/alerts",
        json={
            "product_id": product_id,
            "threshold_percent": str(threshold_percent),
            "active": True,
        },
    )
    print(f"  Status: {resp.status_code}")
    alert = resp.json()
    print(f"  Alert: {alert}")
    return alert


async def simulate_price_drop(product_id: int, original_price: Decimal) -> None:
    """Step 7: Insert a lower price to simulate a drop and test alert logic."""
    print(f"\n{'='*60}")
    print("Step 7: Simulating price drop to test alert notification")
    print(f"{'='*60}")
    print(f"  Original price: {original_price}")
    dropped_price = original_price * Decimal("0.9")  # 10% drop
    print(f"  Simulated drop price: {dropped_price} (10% off)")

    async with AsyncSessionLocal() as db:
        history = PriceHistory(
            product_id=product_id,
            price=dropped_price,
            currency="CNY",
            scraped_at=datetime.now(timezone.utc),
        )
        db.add(history)
        await db.commit()
        print(f"  Saved! History ID: {history.id}")

    # Now run the alert check
    from app.services.crawl import check_price_alerts

    print("\n  Running check_price_alerts()...")
    await check_price_alerts(product_id, dropped_price)
    print("  Done! If price dropped >= threshold, a Feishu notification was sent.")


async def main(url: str):
    """Run the full end-to-end test."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Step 1: Create product
        product = await create_product(client, url)
        product_id = product["id"]

        # Step 2: Crawl price
        crawl_result = await crawl_directly(url)

        if not crawl_result.get("success"):
            print(f"\n[X] Crawl failed: {crawl_result.get('error')}")
            print("\nPossible reasons:")
            print("  - JD anti-bot blocked the request (try with proxy)")
            print("  - Invalid product URL")
            print("  - Network issues")
            return

        price = Decimal(str(crawl_result["price"]))
        currency = crawl_result.get("currency", "CNY")
        title = crawl_result.get("title", "")
        print(f"\n  [OK] Crawled: {title}")
        print(f"     Price: {price} {currency}")

        # Step 3: Save price to DB
        await save_price_to_db(product_id, price, currency)

        # Step 4: Verify product detail
        await verify_product_detail(client, product_id)

        # Step 5: Verify price history
        await verify_price_history(client, product_id)

        # Step 6: Create alert (5% threshold)
        await create_alert_and_test(client, product_id, Decimal("5.00"))

        # Step 7: Simulate price drop and test notification
        await simulate_price_drop(product_id, price)

    print(f"\n{'='*60}")
    print("[OK] End-to-end test complete!")
    print(f"{'='*60}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="JD crawl end-to-end test")
    parser.add_argument("--url", default=DEFAULT_JD_URL, help="JD product URL to test")
    args = parser.parse_args()

    asyncio.run(main(args.url))