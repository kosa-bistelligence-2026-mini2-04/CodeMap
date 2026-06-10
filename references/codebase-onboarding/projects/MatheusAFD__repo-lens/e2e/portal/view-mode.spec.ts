import { expect, test } from '@playwright/test'
import { seedRepository } from '../helpers/seed'

test.describe('Portal — View Mode', () => {
  test('view mode toggle is visible after analysis completes', async ({ page, request }) => {
    const repo = await seedRepository(request, {
      name: 'view-mode-visible-repo',
      fullName: 'test-owner/view-mode-visible-repo',
    })

    await page.goto(`/repos/${repo.id}/analyses`)
    await page.getByRole('button', { name: /new analysis/i }).click()

    await expect(page).toHaveURL(new RegExp(`/repos/${repo.id}/analyses/`), { timeout: 10_000 })

    await expect(page.getByTestId('btn-reanalyze')).toBeVisible({
      timeout: 60_000,
    })

    await expect(page.getByTestId('btn-view-mode-all')).toBeVisible()
    await expect(page.getByTestId('btn-view-mode-product')).toBeVisible()
    await expect(page.getByTestId('btn-view-mode-technical')).toBeVisible()
  })

  test('switching to Product mode hides technical tabs', async ({ page, request }) => {
    const repo = await seedRepository(request, {
      name: 'view-mode-product-repo',
      fullName: 'test-owner/view-mode-product-repo',
    })

    await page.goto(`/repos/${repo.id}/analyses`)
    await page.getByRole('button', { name: /new analysis/i }).click()

    await expect(page).toHaveURL(new RegExp(`/repos/${repo.id}/analyses/`), { timeout: 10_000 })

    await expect(page.getByTestId('btn-reanalyze')).toBeVisible({
      timeout: 60_000,
    })

    await page.getByTestId('btn-view-mode-product').click()

    await expect(page.getByRole('tab', { name: /executive summary/i })).toBeVisible()
    await expect(page.getByRole('tab', { name: /tech stack/i })).not.toBeVisible()
    await expect(page.getByRole('tab', { name: /architecture/i })).not.toBeVisible()
    await expect(page.getByRole('tab', { name: /dependencies/i })).not.toBeVisible()
  })

  test('switching to Technical mode hides product-only tabs', async ({ page, request }) => {
    const repo = await seedRepository(request, {
      name: 'view-mode-technical-repo',
      fullName: 'test-owner/view-mode-technical-repo',
    })

    await page.goto(`/repos/${repo.id}/analyses`)
    await page.getByRole('button', { name: /new analysis/i }).click()

    await expect(page).toHaveURL(new RegExp(`/repos/${repo.id}/analyses/`), { timeout: 10_000 })

    await expect(page.getByTestId('btn-reanalyze')).toBeVisible({
      timeout: 60_000,
    })

    await page.getByTestId('btn-view-mode-technical').click()

    await expect(page.getByRole('tab', { name: /tech stack/i })).toBeVisible()
    await expect(page.getByRole('tab', { name: /security/i })).toBeVisible()
    await expect(page.getByRole('tab', { name: /fun facts/i })).not.toBeVisible()
  })

  test('view mode persists after page reload', async ({ page, request }) => {
    const repo = await seedRepository(request, {
      name: 'view-mode-persist-repo',
      fullName: 'test-owner/view-mode-persist-repo',
    })

    await page.goto(`/repos/${repo.id}/analyses`)
    await page.getByRole('button', { name: /new analysis/i }).click()

    await expect(page).toHaveURL(new RegExp(`/repos/${repo.id}/analyses/`), { timeout: 10_000 })

    await expect(page.getByTestId('btn-reanalyze')).toBeVisible({
      timeout: 60_000,
    })

    await page.getByTestId('btn-view-mode-product').click()
    await expect(page.getByRole('tab', { name: /executive summary/i })).toBeVisible()

    await page.reload()
    await page.waitForLoadState('networkidle')

    await expect(page.getByTestId('btn-view-mode-product')).toBeVisible({ timeout: 15_000 })
    await expect(page.getByRole('tab', { name: /tech stack/i })).not.toBeVisible()
  })
})
