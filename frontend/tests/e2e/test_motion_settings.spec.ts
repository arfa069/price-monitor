import { test, expect } from '@playwright/test'

const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:5173'

test.describe('Motion Settings', () => {
  test.skip(!process.env.E2E_TEST_LOGIN, 'Requires E2E_TEST_LOGIN env var with auth token')

  test.beforeEach(async ({ page }) => {
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
      localStorage.removeItem('price-monitor-motion-speed')
    }, process.env.E2E_TEST_LOGIN!)
  })

  test('should persist transition speed preference', async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`)

    await expect(page.getByText('页面过渡速度')).toBeVisible()
    await page.getByText('慢').click()

    await expect
      .poll(() => page.evaluate(() => localStorage.getItem('price-monitor-motion-speed')))
      .toBe('slow')

    await page.reload()
    await expect(page.locator('.ant-segmented-item-selected')).toContainText('慢')
  })
})
