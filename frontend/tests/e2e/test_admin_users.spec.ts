import { test, expect } from '@playwright/test'

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:5173'

test.describe('Admin Users Page', () => {
  test('should display users table', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/users`)
    await expect(page.locator('.ant-table')).toBeVisible({ timeout: 10000 })
  })

  test('should open new user modal', async ({ page }) => {
    await page.goto(`${BASE_URL}/admin/users`)
    await page.click('button:has-text("新建用户")')
    await expect(page.locator('.ant-modal')).toBeVisible()
  })
})