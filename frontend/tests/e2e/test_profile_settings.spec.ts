import { test, expect } from '@playwright/test'

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:5173'

test.describe('Profile Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/profile`)
  })

  test('should display user info', async ({ page }) => {
    await expect(page.locator('.ant-descriptions')).toBeVisible()
  })

  test('should show profile edit form', async ({ page }) => {
    await expect(page.locator('form')).toBeVisible()
  })

  test('should navigate to settings', async ({ page }) => {
    await page.click('text=账号设置')
    await expect(page).toHaveURL(/\/settings/)
  })
})

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`)
  })

  test('should display settings form', async ({ page }) => {
    await expect(page.locator('form')).toBeVisible()
  })
})