# Platform Adapter Refactoring — Shared Architecture Design

**Date:** 2026-04-24  
**Topic:** Refactor Taobao/JD/Amazon adapters to share common code patterns  
**Status:** Draft → Awaiting User Approval

---

## 1. Problem Statement

The three platform adapters (`taobao.py`, `jd.py`, `amazon.py`) share clear structural patterns but have significant duplication:

| Concern | Taobao | JD | Amazon |
|---------|--------|-----|--------|
| CSS-selector loop for price | ✅ (5 selectors) | ✅ (7 selectors) | ✅ (5 selectors) |
| CSS-selector loop for title | ✅ (4 selectors) | ✅ (7 selectors) | ✅ (3 selectors) |
| Font anti-scraping detection (`?` chars) | ❌ | ✅ | ❌ |
| Cookie injection | ❌ | ✅ (launch mode) | ❌ |
| JS deep-scan fallback | ❌ | ✅ | ❌ |
| Page-title fallback for title | ✅ | ✅ | ❌ |
| Fallback with split on suffix | ❌ | ✅ | ❌ |

**Core issues:**
- `BasePlatformAdapter` defines `extract_price()` and `extract_title()` as abstract methods, but a selector-loop strategy is shared across all three — yet each re-implements it.
- JD's two price strategies (CSS, then JS deep-scan) are tightly bundled inside `JDAdapter.extract_price()`. Taobao could benefit from the CSS strategy but not the JS strategy (different anti-scraping landscape).
- Cookie injection in JD is done by overriding `_init_browser()` entirely; the pattern isn't reusable.
- Price cleaning (strip `¥`, `￥`, `,`, `$`) is duplicated in JD and Amazon; Taobao has its own variant.

---

## 2. Proposed Architecture

### 2.1 Extracted Components

Four reusable components living in `app/platforms/`:

```
app/platforms/
├── base.py              # BasePlatformAdapter (unchanged interface)
├── strategies/
│   ├── __init__.py
│   ├── css_selector.py   # CSSSelectorPriceStrategy, CSSSelectorTitleStrategy
│   ├── js_deep_scan.py   # JSDeeScanPriceStrategy
│   └── anti_scraping.py  # detect_anti_scraping_font(), clean_price_symbols()
├── cookie_injection.py   # parse_cookie_string(), inject_cookies()
└── adapters/
    ├── taobao.py
    ├── jd.py
    └── amazon.py
```

### 2.2 Strategy Interface

```python
from abc import ABC, abstractmethod

class PriceExtractionStrategy(ABC):
    """One way to extract price from a Playwright page."""

    async def extract(self, page: Page) -> float | None:
        """Returns price value or None if this strategy couldn't find it."""
        ...

class TitleExtractionStrategy(ABC):
    """One way to extract title from a Playwright page."""

    async def extract(self, page: Page) -> str | None:
        """Returns title string or None if this strategy couldn't find it."""
        ...
```

### 2.3 CSS Selector Strategy (shared base)

```python
class CSSSelectorPriceStrategy(PriceExtractionStrategy):
    def __init__(self, selectors: list[str], currency: str = "CNY"):
        self.selectors = selectors
        self.currency = currency
        self._anti_scraping_check = True  # JD needs this; Taobao/Amazon don't

    async def extract(self, page: Page) -> float | None:
        for selector in self.selectors:
            # try block + count check + text_content + clean_price_symbols + float parse
            # skip results containing '?' or '？' if self._anti_scraping_check
        return None
```

### 2.4 JS Deep-Scan Strategy (JD only, but reusable interface)

```python
class JSDeeScanPriceStrategy(PriceExtractionStrategy):
    """Scans DOM elements and inline scripts for price data.
    Handles anti-scraping font detection (filters '?' chars)."""

    async def extract(self, page: Page) -> float | None:
        # Move the JS evaluate() block from JDAdapter here.
        # Return float or None.
        ...
```

### 2.5 Chained Strategy Runner

```python
class ChainedPriceStrategy:
    """Runs multiple strategies in sequence; returns first non-None result."""

    def __init__(self, *strategies: PriceExtractionStrategy):
        self._strategies = strategies

    async def extract(self, page: Page) -> float | None:
        for strategy in self._strategies:
            result = await strategy.extract(page)
            if result is not None:
                return result
        return None
```

### 2.6 Cookie Injection Mixin

```python
class CookieInjectionMixin:
    """Provides cookie parsing and injection for launch-mode browsers."""

    @staticmethod
    def parse_cookie_string(cookie_str: str, domain: str) -> list[dict]:
        # Move _parse_cookie_string from JDAdapter here.
        ...

    async def inject_cookies(self, cookie_str: str, domain: str):
        # Common injection logic after _init_browser() in launch mode.
        ...
```

---

## 3. Refactored Adapters

### 3.1 Taobao — simplest, no changes needed to behavior

```python
class TaobaoAdapter(BasePlatformAdapter):
    async def extract_price(self, page):
        strategy = CSSSelectorPriceStrategy(
            selectors=[...], currency="CNY", anti_scraping_check=False
        )
        price = await strategy.extract(page)
        return {"success": price is not None, "price": price, "currency": "CNY"} if price else {"success": False, "error": "Price not found"}
```

### 3.2 JD — uses chained strategy

```python
class JDAdapter(CookieInjectionMixin, BasePlatformAdapter):
    async def _init_browser(self):
        await super()._init_browser()
        if not self._cdp_mode and settings.jd_cookie:
            await self.inject_cookies(settings.jd_cookie, ".jd.com")
            # recreate page after cookie injection (existing behavior)

    async def extract_price(self, page):
        chain = ChainedPriceStrategy(
            CSSSelectorPriceStrategy(JD_PRICE_SELECTORS, anti_scraping_check=True),
            JSDeeScanPriceStrategy(),
        )
        price = await chain.extract(page)
        return {"success": price is not None, "price": price, "currency": "CNY"} if price else {"success": False, "error": "Price not found"}
```

### 3.3 Amazon — uses CSS strategy

```python
class AmazonAdapter(BasePlatformAdapter):
    async def extract_price(self, page):
        strategy = CSSSelectorPriceStrategy(
            selectors=[...], currency="USD", anti_scraping_check=False
        )
        # Amazon has dynamic currency detection — could be a flag or separate strategy
```

---

## 4. Key Design Decisions

### 4.1 Strategy composition over inheritance
Use `ChainedPriceStrategy` to combine approaches rather than building them into class hierarchies. New platforms compose from existing strategies.

### 4.2 Anti-scraping toggle per strategy
JD needs font detection; Taobao/Amazon don't. Pass `_anti_scraping_check=False` to disable it rather than subclassing.

### 4.3 CookieInjectionMixin uses composition
`inject_cookies()` is called from `_init_browser()` after `super()._init_browser()`. No deep inheritance needed.

### 4.4 JS deep scan stays encapsulated
The JS evaluate block in `JSDeeScanPriceStrategy` is JD-specific anti-scraping logic but lives in a reusable class. Other platforms can opt in if they encounter similar protection.

---

## 5. Migration Path

**Phase 1:** Create `strategies/css_selector.py` and `strategies/anti_scraping.py`. Verify Taobao still works identically with the new CSS strategy.

**Phase 2:** Create `strategies/js_deep_scan.py` and `cookie_injection.py`. Refactor JDAdapter to use `ChainedPriceStrategy`. Verify identical behavior.

**Phase 3:** Refactor AmazonAdapter. Extract `clean_price_symbols()` utility if helpful.

**Phase 4:** Remove duplicated code from each adapter. Add tests for each strategy in isolation.

---

## 6. Estimated Impact

| Metric | Before | After |
|--------|--------|-------|
| Lines in `jd.py` | ~205 | ~80 (browser init + strategy wiring only) |
| Lines in `taobao.py` | ~66 | ~40 |
| Lines in `amazon.py` | ~70 | ~40 |
| Shared strategy modules | 0 | 4 new files |
| Code duplication | High (price cleaning, selector loops) | Minimal |

---

## 7. Open Questions

1. **Should we also extract `extract_title` into a `ChainedTitleStrategy`**? Title extraction is simpler (single strategy per platform so far), but the CSS selector loop pattern is identical. Worth unifying?
2. **Currency detection for Amazon**: The current code inspects the price text for `¥` to set `currency = "CNY"`. Should this be a separate `CurrencyDetectionStrategy` or just a flag on `CSSSelectorPriceStrategy`?
3. **Should Taobao also get JS deep-scan as an optional second strategy**? The JS scan is expensive (runs in page context) but robust. Want to offer it as an opt-in for Taobao too?