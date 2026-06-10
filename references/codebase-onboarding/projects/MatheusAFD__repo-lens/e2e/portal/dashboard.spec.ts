import { test, expect } from '@playwright/test'
import { seedRepository, GITHUB_REPOS_FIXTURE } from '../helpers/seed'

test.describe('Portal — Dashboard', () => {
  test.describe('repo list', () => {
    test('shows repo card with name and language badge after adding', async ({ page, request }) => {
      await seedRepository(request, {
        owner: 'test-owner',
        name: 'dashboard-test-repo',
        fullName: 'test-owner/dashboard-test-repo',
        language: 'TypeScript',
      })

      await page.goto('/dashboard')
      await page.waitForLoadState('networkidle')

      const repoCard = page.locator(
        '[data-testid="repo-card"][data-repo-name="dashboard-test-repo"]',
      )
      await expect(repoCard.getByRole('heading', { name: 'dashboard-test-repo' })).toBeVisible()
      await expect(repoCard.getByText('TypeScript')).toBeVisible()
    })

    test('repo card shows "View Analyses" button', async ({ page, request }) => {
      await seedRepository(request, {
        owner: 'test-owner',
        name: 'analyses-btn-repo',
        fullName: 'test-owner/analyses-btn-repo',
      })

      await page.goto('/dashboard')
      await page.waitForLoadState('networkidle')

      const repoCard = page.locator('[data-testid="repo-card"][data-repo-name="analyses-btn-repo"]')
      await expect(repoCard.getByRole('button', { name: /view analyses/i })).toBeVisible()
    })

    test('"View Analyses" button navigates to analyses list', async ({ page, request }) => {
      const repo = await seedRepository(request, {
        owner: 'test-owner',
        name: 'nav-test-repo',
        fullName: 'test-owner/nav-test-repo',
      })

      await page.goto('/dashboard')
      await page.waitForLoadState('networkidle')

      const repoCard = page.locator('[data-testid="repo-card"][data-repo-name="nav-test-repo"]')
      await repoCard.getByRole('button', { name: /view analyses/i }).click()
      await expect(page).toHaveURL(new RegExp(`/repos/${repo.id}/analyses`))
    })
  })

  test.describe('add repository dialog', () => {
    test.beforeEach(async ({ page }) => {
      await page.goto('/dashboard')
      await page.waitForLoadState('networkidle')
    })

    test('clicking "Add repository" opens dialog', async ({ page }) => {
      await page
        .getByRole('button', { name: /add repository/i })
        .first()
        .click()
      await expect(page.getByRole('dialog')).toBeVisible()
    })

    test('dialog shows GitHub repos from mock', async ({ page }) => {
      await page.route('**/github/repos', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(GITHUB_REPOS_FIXTURE),
        })
      })

      await page
        .getByRole('button', { name: /add repository/i })
        .first()
        .click()

      await expect(page.getByText('test-owner/my-awesome-repo')).toBeVisible()
      await expect(page.getByText('test-owner/another-repo')).toBeVisible()
    })

    test('dialog shows empty state when GitHub returns no repos', async ({ page }) => {
      await page.route('**/github/repos', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([]),
        })
      })

      await page
        .getByRole('button', { name: /add repository/i })
        .first()
        .click()

      await expect(page.getByText(/no repositories found/i)).toBeVisible()
    })

    test('clicking "Add" on a repo from dialog closes dialog and shows repo in list', async ({
      page,
    }) => {
      await page.route('**/github/repos', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(GITHUB_REPOS_FIXTURE),
        })
      })

      await page
        .getByRole('button', { name: /add repository/i })
        .first()
        .click()
      await expect(page.getByText('test-owner/my-awesome-repo')).toBeVisible()

      await page.getByRole('button', { name: /^add$/i }).first().click()

      await expect(page.getByRole('dialog')).not.toBeVisible()
      await expect(page.getByText('my-awesome-repo')).toBeVisible()
    })
  })
})
