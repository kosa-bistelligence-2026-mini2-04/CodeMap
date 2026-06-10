import { test, expect } from '@playwright/test'
import { seedRepository } from '../helpers/seed'

test.describe('Portal — Repos', () => {
  test.describe('analyses list page (/repos/:id/analyses)', () => {
    test('shows empty state when no analyses exist', async ({ page, request }) => {
      const repo = await seedRepository(request, {
        name: 'empty-analyses-repo',
        fullName: 'test-owner/empty-analyses-repo',
      })

      await page.goto(`/repos/${repo.id}/analyses`)

      await expect(page.getByText(/no analyses/i)).toBeVisible()
      await expect(page.getByRole('button', { name: /new analysis/i })).toBeVisible()
    })

    test('shows repo name in page heading', async ({ page, request }) => {
      const repo = await seedRepository(request, {
        name: 'heading-test-repo',
        fullName: 'test-owner/heading-test-repo',
      })

      await page.goto(`/repos/${repo.id}/analyses`)

      await expect(page.getByRole('heading', { name: 'heading-test-repo' })).toBeVisible()
    })

    test('"New Analysis" button starts analysis and navigates to analysis detail', async ({
      page,
      request,
    }) => {
      const repo = await seedRepository(request, {
        name: 'nav-analysis-repo',
        fullName: 'test-owner/nav-analysis-repo',
      })

      await page.goto(`/repos/${repo.id}/analyses`)
      await page.waitForLoadState('networkidle')
      await page.getByRole('button', { name: /new analysis/i }).click()

      await expect(page).toHaveURL(new RegExp(`/repos/${repo.id}/analyses/`), { timeout: 10_000 })
    })
  })
})
