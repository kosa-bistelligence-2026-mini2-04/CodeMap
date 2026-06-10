import { test, expect } from '@playwright/test'

test.describe('Portal — Sign Out', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard')
    await page.waitForLoadState('networkidle')
    await page.getByTestId('user-menu-trigger').waitFor({ state: 'visible' })
  })

  test('user menu button is visible when authenticated', async ({ page }) => {
    await expect(page.getByTestId('user-menu-trigger')).toBeVisible()
  })

  test('clicking sign out redirects to root or sign-in page', async ({ page }) => {
    await page.getByTestId('user-menu-trigger').click()
    await page.getByRole('menuitem', { name: /sign out/i }).click()

    await expect(page).toHaveURL(/\/$|\/auth\/sign-in/)
  })

  test('after sign out, navigating to /dashboard redirects to /auth/sign-in', async ({ page }) => {
    await page.getByTestId('user-menu-trigger').click()
    await page.getByRole('menuitem', { name: /sign out/i }).click()
    await page.waitForURL(/\/$|\/auth\/sign-in/)

    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/auth\/sign-in/)
  })
})
