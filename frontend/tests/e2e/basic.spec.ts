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
const API_URL = process.env.E2E_API_URL || 'http://localhost:8000'

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
    // Set auth token
    await page.evaluate((token) => {
      localStorage.setItem('auth_token', token)
    }, process.env.E2E_TEST_LOGIN!)

    await page.goto(`${BASE_URL}/products`)
    await expect(page.locator('.ant-table')).toBeVisible({ timeout: 10000 })
  })
})

test.describe('Jobs Page (after login)', () => {
  test.skip(!process.env.E2E_TEST_LOGIN, 'Requires E2E_TEST_LOGIN env var with auth token')

  test('should display jobs page', async ({ page }) => {
    await page.evaluate((token) => {
      localStorage.setItem('auth_token', token)
    }, process.env.E2E_TEST_LOGIN!)

    await page.goto(`${BASE_URL}/jobs`)
    await expect(page.locator('.ant-table').or(page.locator('.ant-empty'))).toBeVisible({ timeout: 10000 })
  })
})
