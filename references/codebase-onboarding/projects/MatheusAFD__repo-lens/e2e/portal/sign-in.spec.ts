import { test, expect } from '@playwright/test'
import { TEST_USER } from '../helpers/fixtures'

test.use({ storageState: { cookies: [], origins: [] } })

test.describe('Portal — Sign In', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/auth/sign-in')
    await page.waitForLoadState('networkidle')
  })

  test.describe('form validation', () => {
    test('submitting empty form shows required field errors', async ({ page }) => {
      await page.getByRole('button', { name: /sign in/i }).click()
      await expect(page.getByText(/email is required/i)).toBeVisible()
      await expect(page.getByText(/password is required/i)).toBeVisible()
    })

    test('invalid email format shows format error', async ({ page }) => {
      await page.getByLabel('Email').fill('not-valid')
      await page.getByRole('button', { name: /sign in/i }).click()
      await expect(page.getByText(/invalid email/i)).toBeVisible()
    })
  })

  test.describe('wrong credentials', () => {
    test('shows error message and stays on sign-in page', async ({ page }) => {
      await page.getByLabel('Email').fill(TEST_USER.email)
      await page.getByLabel('Password').fill('WrongPassword')
      await page.getByRole('button', { name: /sign in/i }).click()

      await expect(page).toHaveURL(/\/auth\/sign-in/)
      await expect(page.getByText(/invalid|incorrect|wrong|credentials/i)).toBeVisible()
    })
  })

  test.describe('successful sign-in', () => {
    test('redirects to /dashboard after correct credentials', async ({ page }) => {
      await page.getByLabel('Email').fill(TEST_USER.email)
      await page.getByLabel('Password').fill(TEST_USER.password)
      await page.getByRole('button', { name: /sign in/i }).click()

      await expect(page).toHaveURL('/dashboard', { timeout: 15000 })
    })
  })

  test('has link to create account page', async ({ page }) => {
    await expect(page.getByRole('link', { name: /create account/i })).toBeVisible()
  })
})
