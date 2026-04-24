# Platform Adapter Refactoring Plan

**Date:** 2026-04-24
**Branch:** refactor/platform-adapter-strategies
**Status:** In Progress

## Overview

Refactor platform adapters (taobao.py, jd.py) to use a strategy pattern for price extraction, making the code more maintainable and extensible.

## Current State

- `BasePlatformAdapter` in `base.py` - abstract base with browser init, crawl orchestration
- `TaobaoAdapter` in `taobao.py` - simple CSS selector-based price extraction, no strategy pattern
- `JDAdapter` in `jd.py` - has basic cookie injection + js_deep_scan inline in `extract_price`

## Target State

- Strategy pattern for price extraction (CSS selector, JS deep scan, cookie injection)
- Strategies are composable and configurable per platform
- Clean separation between browser management and price extraction logic

---

## Phase 1: Create Strategy Classes + Refactor Taobao

### Task 1.1: Create `PriceExtractionStrategy` base class

Create `app/platforms/strategies/base.py`:
- Abstract base `PriceExtractionStrategy` with `async def extract(self, page) -> Dict[str, Any]`
- Method returns `{"success": bool, "price": float, "currency": str, "method": str}`

### Task 1.2: Create `CSSSelectorStrategy`

Create `app/platforms/strategies/css_selector.py`:
- Takes list of CSS selectors in constructor
- Tries each selector, returns first valid price
- Returns method name "css_selector"

### Task 1.3: Create `JSDeeScanStrategy`

Create `app/platforms/strategies/js_deep_scan.py`:
- Runs JavaScript to scan elements and scripts for price data
- Reuses the JD inline JS logic (extract jdPrice, skuPrice from scripts)
- Returns method name "js_deep_scan"

### Task 1.4: Refactor TaobaoAdapter to use strategies

Modify `taobao.py`:
- Use `CSSSelectorStrategy` as primary
- Add configurable `JSDeeScanStrategy` as fallback
- Keep existing selectors

### Task 1.5: Create strategies __init__ and export

Create `app/platforms/strategies/__init__.py` exporting all strategies.

---

## Phase 2: Create cookie_injection + js_deep_scan + refactor jd.py

### Task 2.1: Create `CookieInjectionMiddleware`

Create `app/platforms/middleware/cookie_injection.py`:
- Standalone middleware class that can be mixed into any adapter
- `_inject_cookies(cookie_str)` method to parse and inject cookies
- Used by JD but applicable to other platforms

### Task 2.2: Formalize JSDeeScanStrategy (already exists inline in JD)

- Move the inline JS price scanning from jd.py into `JSDeeScanStrategy`
- JD's `extract_price` already has JS deep scan logic — extract it

### Task 2.3: Refactor JDAdapter to use strategies

Modify `jd.py`:
- Use `CookieInjectionMiddleware` for cookie injection (remove inline cookie parsing)
- Use `JSDeeScanStrategy` for price extraction (remove inline JS)
- Use `CSSSelectorStrategy` for direct selectors

---

## Phase 3: Add JS deep-scan to Taobao (configurable)

### Task 3.1: Add `taobao_js_deep_scan` config option

Add `taobao_js_deep_scan_enabled: bool = False` to `Settings` in `config.py`.

### Task 3.2: Make TaobaoAdapter accept js_deep_scan as optional fallback

- Pass `js_deep_scan_enabled` from settings to TaobaoAdapter
- When enabled, use `JSDeeScanStrategy` after CSS selectors fail

---

## Phase 4: Verification

### Task 4.1: Run existing tests

```bash
pytest tests/ -v
```

### Task 4.2: Manual smoke test (if possible)

Verify adapters can be instantiated and have strategy attributes.

---

## Phase 5: Unit Tests

### Task 5.1: Write tests for CSSSelectorStrategy

`tests/test_strategies.py`:
- Test successful price extraction with valid selector
- Test fallback to second selector when first fails
- Test returns correct method name

### Task 5.2: Write tests for JSDeeScanStrategy

`tests/test_strategies.py`:
- Test price extraction from script content
- Test price extraction from DOM elements
- Test anti-scraping character detection

### Task 5.3: Write tests for CookieInjectionMiddleware

`tests/test_strategies.py`:
- Test cookie string parsing
- Test cookie injection

### Task 5.4: Write tests for refactored adapters

`tests/test_platforms.py`:
- Test TaobaoAdapter has strategies attribute
- Test JDAdapter uses cookie middleware
- Test adapter instantiation (mocked browser)

---

## Files to Create

```
app/platforms/strategies/
  __init__.py
  base.py
  css_selector.py
  js_deep_scan.py
app/platforms/middleware/
  __init__.py
  cookie_injection.py
tests/test_strategies.py
tests/test_platforms.py (new)
```

## Files to Modify

```
app/platforms/taobao.py  (Phase 1)
app/platforms/jd.py      (Phase 2)
app/config.py            (Phase 3)
```

## Acceptance Criteria

1. All strategies have base class and concrete implementations
2. Taobao uses CSSSelectorStrategy + optional JSDeeScanStrategy
3. JD uses CookieInjectionMiddleware + JSDeeScanStrategy + CSSSelectorStrategy
4. All new files have type hints and docstrings
5. All new code passes ruff checks
6. Tests cover strategy behavior with mocked pages