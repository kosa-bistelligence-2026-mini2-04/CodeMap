import { test, expect } from '@playwright/test'

test.use({ storageState: { cookies: [], origins: [] } })

test.describe('Portal — Auth Redirects', () => {
  test.describe('when not authenticated', () => {
    test('root page renders landing page', async ({ page }) => {
      await page.goto('/')
      await expect(page).toHaveURL('/')
      await expect(page.getByRole('heading', { name: /understand any/i })).toBeVisible()
    })

    test('dashboard redirects to /auth/sign-in', async ({ page }) => {
      await page.goto('/dashboard')
      await expect(page).toHaveURL(/\/auth\/sign-in/)
    })

    test('/analyze/:repoId redirects to /auth/sign-in', async ({ page }) => {
      await page.goto('/analyze/some-repo-id')
      await expect(page).toHaveURL(/\/auth\/sign-in/)
    })

    test('/repos/:id/analyses redirects to /auth/sign-in', async ({ page }) => {
      await page.goto('/repos/some-repo-id/analyses')
      await expect(page).toHaveURL(/\/auth\/sign-in/)
    })

    test('/repos/:id/analyses/:analysisId redirects to /auth/sign-in', async ({ page }) => {
      await page.goto('/repos/some-repo-id/analyses/some-analysis-id')
      await expect(page).toHaveURL(/\/auth\/sign-in/)
    })

    test('sign-in page renders login form', async ({ page }) => {
      await page.goto('/auth/sign-in')
      await expect(page.getByLabel('Email')).toBeVisible()
      await expect(page.getByLabel('Password')).toBeVisible()
      await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible()
    })
  })
})
