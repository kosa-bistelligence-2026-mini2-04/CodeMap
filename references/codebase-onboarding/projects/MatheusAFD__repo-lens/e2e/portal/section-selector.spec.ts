import { expect, test } from '@playwright/test'
import { seedRepository } from '../helpers/seed'

test.describe('Portal — Section Selector', () => {
  test('dialog opens when clicking Re-analyze after analysis completes', async ({
    page,
    request,
  }) => {
    const repo = await seedRepository(request, {
      name: 'section-selector-repo',
      fullName: 'test-owner/section-selector-repo',
    })

    await page.goto(`/repos/${repo.id}/analyses`)
    await page.getByRole('button', { name: /new analysis/i }).click()

    await expect(page).toHaveURL(new RegExp(`/repos/${repo.id}/analyses/`), { timeout: 10_000 })

    const reanalyzeButton = page.getByTestId('btn-reanalyze')
    await expect(reanalyzeButton).toBeVisible({ timeout: 60_000 })
    await reanalyzeButton.click()

    await expect(page.getByRole('dialog')).toBeVisible()
    await expect(page.getByText('Configure Analysis')).toBeVisible()
  })

  test('dialog shows section checkboxes with Recommended badges', async ({ page, request }) => {
    const repo = await seedRepository(request, {
      name: 'section-selector-badges-repo',
      fullName: 'test-owner/section-selector-badges-repo',
    })

    await page.goto(`/repos/${repo.id}/analyses`)
    await page.getByRole('button', { name: /new analysis/i }).click()

    await expect(page).toHaveURL(new RegExp(`/repos/${repo.id}/analyses/`), { timeout: 10_000 })

    const reanalyzeButton = page.getByTestId('btn-reanalyze')
    await expect(reanalyzeButton).toBeVisible({ timeout: 60_000 })
    await reanalyzeButton.click()

    const dialog = page.getByRole('dialog')
    await expect(dialog.getByRole('checkbox', { name: /executive summary/i })).toBeVisible()
    await expect(dialog.getByRole('checkbox', { name: /security/i })).toBeVisible()
    await expect(dialog.getByText('Recommended').first()).toBeVisible()
  })

  test('custom context field accepts text', async ({ page, request }) => {
    const repo = await seedRepository(request, {
      name: 'custom-context-repo',
      fullName: 'test-owner/custom-context-repo',
    })

    await page.goto(`/repos/${repo.id}/analyses`)
    await page.getByRole('button', { name: /new analysis/i }).click()

    await expect(page).toHaveURL(new RegExp(`/repos/${repo.id}/analyses/`), { timeout: 10_000 })

    const reanalyzeButton = page.getByTestId('btn-reanalyze')
    await expect(reanalyzeButton).toBeVisible({ timeout: 60_000 })
    await reanalyzeButton.click()

    const textarea = page.getByLabel(/additional context/i)
    await expect(textarea).toBeVisible()
    await textarea.fill('This is a B2B SaaS project')
    await expect(textarea).toHaveValue('This is a B2B SaaS project')
  })

  test('Start Analysis button is disabled when no section is selected', async ({
    page,
    request,
  }) => {
    const repo = await seedRepository(request, {
      name: 'no-section-repo',
      fullName: 'test-owner/no-section-repo',
    })

    await page.goto(`/repos/${repo.id}/analyses`)
    await page.getByRole('button', { name: /new analysis/i }).click()

    await expect(page).toHaveURL(new RegExp(`/repos/${repo.id}/analyses/`), { timeout: 10_000 })

    const reanalyzeButton = page.getByTestId('btn-reanalyze')
    await expect(reanalyzeButton).toBeVisible({ timeout: 60_000 })
    await reanalyzeButton.click()

    const dialog = page.getByRole('dialog')

    const checkboxes = dialog.getByRole('checkbox')
    const count = await checkboxes.count()
    for (let i = 0; i < count; i++) {
      const checkbox = checkboxes.nth(i)
      const checked = await checkbox.isChecked()
      if (checked) await checkbox.click()
    }

    await expect(dialog.getByRole('button', { name: /start analysis/i })).toBeDisabled()
  })
})
