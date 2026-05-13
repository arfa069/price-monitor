import { test, expect } from '@playwright/test'

/**
 * Frontend UI interaction tests using Playwright.
 *
 * Prerequisites:
 *   1. Backend server running on http://localhost:8000
 *   2. Frontend dev server running on http://localhost:5173
 *
 * Run with: npx playwright test tests/e2e/
 *
 * Note: These tests require real browser interaction and are marked as
 * slow tests. They are skipped by default in CI environments.
 */
const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:5173'

async function setAuthToken(page: import('@playwright/test').Page) {
  await page.addInitScript((token) => {
    localStorage.setItem('auth_token', token)
    localStorage.setItem(
      'auth_user',
      JSON.stringify({
        id: 1,
        username: 'e2e',
        email: 'e2e@example.com',
        role: 'super_admin',
        is_active: true,
      }),
    )
  }, process.env.E2E_TEST_LOGIN!)
}

test.describe('Login Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/login`)
  })

  test('should display login form', async ({ page }) => {
    await expect(page.locator('input[placeholder*="用户名"]')).toBeVisible()
    await expect(page.locator('input[type="password"]')).toBeVisible()
    await expect(page.locator('button[type="submit"]')).toBeVisible()
  })

  test('should show validation errors for empty fields', async ({ page }) => {
    await page.click('button[type="submit"]')
    await expect(page.locator('.ant-form-item-explain-error').first()).toBeVisible()
  })

  test('should navigate to register page', async ({ page }) => {
    await page.click('a[href="/register"]')
    await expect(page).toHaveURL(/\/register/)
  })
})

test.describe('Register Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/register`)
  })

  test('should display registration form', async ({ page }) => {
    await expect(page.locator('input[placeholder*="用户名"]')).toBeVisible()
    await expect(page.locator('input[placeholder*="邮箱"]')).toBeVisible()
    await expect(page.locator('input[type="password"]')).toBeVisible()
    await expect(page.locator('button[type="submit"]')).toBeVisible()
  })

  test('should navigate to login page', async ({ page }) => {
    await page.click('a[href="/login"]')
    await expect(page).toHaveURL(/\/login/)
  })
})

test.describe('Products Page (after login)', () => {
  test.skip(!process.env.E2E_TEST_LOGIN, 'Requires E2E_TEST_LOGIN env var with auth token')

  test('should display products table', async ({ page }) => {
    await setAuthToken(page)

    await page.goto(`${BASE_URL}/products`)
    await expect(page.locator('.ant-table')).toBeVisible({ timeout: 10000 })
  })
})

test.describe('Jobs Page (after login)', () => {
  test.skip(!process.env.E2E_TEST_LOGIN, 'Requires E2E_TEST_LOGIN env var with auth token')

  test('should display jobs page', async ({ page }) => {
    await setAuthToken(page)

    await page.goto(`${BASE_URL}/jobs`)
    await expect(page.locator('.ant-table').or(page.locator('.ant-empty'))).toBeVisible({ timeout: 10000 })
  })

  test('should keep transition wrapper visible when switching pages', async ({ page }) => {
    await setAuthToken(page)

    await page.goto(`${BASE_URL}/jobs`)
    await expect(page.locator('[data-page-transition="/jobs"]')).toBeVisible({ timeout: 10000 })

    await page.click('text=商品管理')
    await expect(page).toHaveURL(/\/products/)
    await expect(page.locator('[data-page-transition="/products"]')).toBeVisible({ timeout: 10000 })

    await page.click('text=定时配置')
    await expect(page).toHaveURL(/\/schedule/)
    await expect(page.locator('[data-page-transition="/schedule"]')).toBeVisible({ timeout: 10000 })
  })
})
