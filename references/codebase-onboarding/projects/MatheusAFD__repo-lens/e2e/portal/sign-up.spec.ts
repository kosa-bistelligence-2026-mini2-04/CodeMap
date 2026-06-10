import { test, expect, request as playwrightRequest } from '@playwright/test'

const DUPLICATE_EMAIL = `e2e-duplicate-${Date.now()}@repo-lens.dev`

test.use({ storageState: { cookies: [], origins: [] } })

test.describe('Portal — Sign Up', () => {
  test.beforeAll(async () => {
    const apiContext = await playwrightRequest.newContext()
    await apiContext.post('http://localhost:4001/api/auth/sign-up/email', {
      data: { name: 'Pre-existing User', email: DUPLICATE_EMAIL, password: 'TestPassword123' },
    })
    await apiContext.dispose()
  })

  test.beforeEach(async ({ page }) => {
    await page.goto('/auth/sign-up')
    await page.waitForLoadState('networkidle')
  })

  test.describe('form validation', () => {
    test('submitting empty form shows required field errors', async ({ page }) => {
      await page.getByRole('button', { name: /create account/i }).click()
      await expect(page.getByText(/name is required/i)).toBeVisible()
      await expect(page.getByText(/email is required/i)).toBeVisible()
      await expect(page.getByText(/at least 8/i)).toBeVisible()
    })

    test('invalid email shows email format error', async ({ page }) => {
      await page.getByLabel('Email').fill('not-an-email')
      await page.getByRole('button', { name: /create account/i }).click()
      await expect(page.getByText(/invalid email/i)).toBeVisible()
    })

    test('password shorter than 8 chars shows length error', async ({ page }) => {
      await page.getByLabel('Password').fill('short')
      await page.getByRole('button', { name: /create account/i }).click()
      await expect(page.getByText(/at least 8/i)).toBeVisible()
    })
  })

  test.describe('successful registration', () => {
    test('fills form, submits and lands on /dashboard', async ({ page }) => {
      const uniqueEmail = `e2e-signup-${Date.now()}@repo-lens.dev`

      await page.getByLabel('Name').fill('New E2E User')
      await page.getByLabel('Email').fill(uniqueEmail)
      await page.getByLabel('Password').fill('TestPassword123')
      await page.getByRole('button', { name: /create account/i }).click()

      await expect(page).toHaveURL('/dashboard', { timeout: 15000 })
    })
  })

  test.describe('duplicate account', () => {
    test('shows error when registering with already-used email', async ({ page }) => {
      await page.getByLabel('Name').fill('Duplicate User')
      await page.getByLabel('Email').fill(DUPLICATE_EMAIL)
      await page.getByLabel('Password').fill('TestPassword123')
      await page.getByRole('button', { name: /create account/i }).click()

      await expect(page.getByText(/already|exists|registered/i)).toBeVisible()
    })
  })

  test('has link to sign-in page', async ({ page }) => {
    await expect(page.getByRole('link', { name: /sign in/i })).toBeVisible()
  })
})
