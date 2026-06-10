import { expect, test } from '@playwright/test'
import { seedRepository } from '../helpers/seed'

test.describe('Portal — Copy AI Fix Instructions', () => {
  test('Copy AI Fix Instructions button is visible after analysis completes', async ({
    page,
    request,
  }) => {
    const repo = await seedRepository(request, {
      name: 'copy-prompt-visible-repo',
      fullName: 'test-owner/copy-prompt-visible-repo',
    })

    await page.goto(`/repos/${repo.id}/analyses`)
    await page.getByRole('button', { name: /new analysis/i }).click()

    await expect(page).toHaveURL(new RegExp(`/repos/${repo.id}/analyses/`), { timeout: 10_000 })

    await expect(page.getByTestId('btn-reanalyze')).toBeVisible({
      timeout: 60_000,
    })

    await expect(page.getByTestId('btn-copy-agent-prompt')).toBeVisible()
  })

  test('clicking Copy AI Fix Instructions writes text to clipboard', async ({ page, request }) => {
    const repo = await seedRepository(request, {
      name: 'copy-prompt-clipboard-repo',
      fullName: 'test-owner/copy-prompt-clipboard-repo',
    })

    await page.goto(`/repos/${repo.id}/analyses`)
    await page.getByRole('button', { name: /new analysis/i }).click()

    await expect(page).toHaveURL(new RegExp(`/repos/${repo.id}/analyses/`), { timeout: 10_000 })

    await expect(page.getByTestId('btn-reanalyze')).toBeVisible({
      timeout: 60_000,
    })

    await page.context().grantPermissions(['clipboard-read', 'clipboard-write'])

    await page.getByTestId('btn-copy-agent-prompt').click()

    const clipboardText = await page.evaluate(() => navigator.clipboard.readText())

    expect(clipboardText).toContain('You are an expert developer')
    expect(clipboardText.length).toBeGreaterThan(50)
  })
})
