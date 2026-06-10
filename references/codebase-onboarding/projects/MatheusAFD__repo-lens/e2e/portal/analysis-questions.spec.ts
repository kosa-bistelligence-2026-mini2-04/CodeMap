import { expect, test } from '@playwright/test'
import { seedRepository } from '../helpers/seed'

test.describe('Portal — Analysis Questions', () => {
  test('Ask tab is visible after analysis completes', async ({ page, request }) => {
    const repo = await seedRepository(request, {
      name: 'questions-tab-repo',
      fullName: 'test-owner/questions-tab-repo',
    })

    await page.goto(`/repos/${repo.id}/analyses`)
    await page.getByRole('button', { name: /new analysis/i }).click()

    await expect(page).toHaveURL(new RegExp(`/repos/${repo.id}/analyses/`), { timeout: 10_000 })

    await expect(page.getByTestId('btn-reanalyze')).toBeVisible({
      timeout: 60_000,
    })

    await expect(page.getByRole('tab', { name: /ask/i })).toBeVisible()
  })

  test('Ask tab shows question input', async ({ page, request }) => {
    const repo = await seedRepository(request, {
      name: 'questions-input-repo',
      fullName: 'test-owner/questions-input-repo',
    })

    await page.goto(`/repos/${repo.id}/analyses`)
    await page.getByRole('button', { name: /new analysis/i }).click()

    await expect(page).toHaveURL(new RegExp(`/repos/${repo.id}/analyses/`), { timeout: 10_000 })

    await expect(page.getByTestId('btn-reanalyze')).toBeVisible({
      timeout: 60_000,
    })

    await page.getByRole('tab', { name: /ask/i }).click()

    await expect(page.getByPlaceholder(/ask a question/i)).toBeVisible()
    await expect(page.getByTestId('btn-ask-send')).toBeVisible()
  })

  test('submitting a question calls the ask endpoint and shows response', async ({
    page,
    request,
  }) => {
    const repo = await seedRepository(request, {
      name: 'questions-submit-repo',
      fullName: 'test-owner/questions-submit-repo',
    })

    await page.goto(`/repos/${repo.id}/analyses`)
    await page.getByRole('button', { name: /new analysis/i }).click()

    await expect(page).toHaveURL(new RegExp(`/repos/${repo.id}/analyses/`), { timeout: 10_000 })

    await expect(page.getByTestId('btn-reanalyze')).toBeVisible({
      timeout: 60_000,
    })

    await page.route('**/analysis/*/ask', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body: [
            'data: {"type":"progress","message":"This is a test answer."}\n\n',
            'data: {"type":"done","analysisId":"mock-q-id"}\n\n',
          ].join(''),
        })
      } else {
        await route.continue()
      }
    })

    await page.getByRole('tab', { name: /ask/i }).click()

    const input = page.getByPlaceholder(/ask a question/i)
    await input.fill('What does this project do?')
    await page.getByTestId('btn-ask-send').click()

    await expect(page.getByText('What does this project do?')).toBeVisible({ timeout: 10_000 })
  })
})
