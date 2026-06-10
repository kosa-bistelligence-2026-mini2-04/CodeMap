import { test, expect } from '@playwright/test'
import { seedRepository } from '../helpers/seed'

const SECTION_LABELS = [
  'Executive Summary',
  'Tech Stack',
  'Architecture',
  'Security',
  'Dependencies',
  'Update Plan',
  'Recommendations',
  'Code Metrics',
  'Fun Facts',
]

test.describe('Portal — Analysis', () => {
  test('starting analysis from analyses list navigates to analysis page', async ({
    page,
    request,
  }) => {
    const repo = await seedRepository(request, {
      name: 'streaming-test-repo',
      fullName: 'test-owner/streaming-test-repo',
    })

    await page.goto(`/repos/${repo.id}/analyses`)
    await page.getByRole('button', { name: /new analysis/i }).click()

    await expect(page).toHaveURL(new RegExp(`/repos/${repo.id}/analyses/`), { timeout: 10_000 })
  })

  test('after stream completes all 9 section tabs are visible', async ({ page, request }) => {
    const repo = await seedRepository(request, {
      name: 'full-analysis-repo',
      fullName: 'test-owner/full-analysis-repo',
    })

    await page.goto(`/repos/${repo.id}/analyses`)
    await page.getByRole('button', { name: /new analysis/i }).click()

    await expect(page).toHaveURL(new RegExp(`/repos/${repo.id}/analyses/`), { timeout: 10_000 })

    for (const label of SECTION_LABELS) {
      await expect(page.getByRole('tab', { name: new RegExp(label, 'i') })).toBeVisible({
        timeout: 60_000,
      })
    }
  })

  test('"Re-analyze" button is visible after analysis completes', async ({ page, request }) => {
    const repo = await seedRepository(request, {
      name: 're-analyze-repo',
      fullName: 'test-owner/re-analyze-repo',
    })

    await page.goto(`/repos/${repo.id}/analyses`)
    await page.getByRole('button', { name: /new analysis/i }).click()

    await expect(page).toHaveURL(new RegExp(`/repos/${repo.id}/analyses/`), { timeout: 10_000 })

    await expect(page.getByTestId('btn-reanalyze')).toBeVisible({
      timeout: 60_000,
    })
  })

  test('clicking section tab changes visible content', async ({ page, request }) => {
    const repo = await seedRepository(request, {
      name: 'tab-navigation-repo',
      fullName: 'test-owner/tab-navigation-repo',
    })

    await page.goto(`/repos/${repo.id}/analyses`)
    await page.getByRole('button', { name: /new analysis/i }).click()

    await expect(page).toHaveURL(new RegExp(`/repos/${repo.id}/analyses/`), { timeout: 10_000 })

    const securityTab = page.getByRole('tab', { name: /security/i })
    await expect(securityTab).toBeVisible({ timeout: 60_000 })
    await securityTab.click()

    await expect(page.getByText(/grade|owasp|vulnerabilit/i)).toBeVisible()
  })
})
