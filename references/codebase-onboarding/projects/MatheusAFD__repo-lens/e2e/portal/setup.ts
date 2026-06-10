import { test as setup } from '@playwright/test'
import * as path from 'node:path'
import { fileURLToPath } from 'node:url'
import { TEST_USER } from '../helpers/fixtures'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

const authFile = path.join(__dirname, '../.auth/user.json')

setup('create test user and authenticate', async ({ page, request }) => {
  await request.post('http://localhost:4001/api/auth/sign-up/email', {
    data: TEST_USER,
  })

  await page.goto('/auth/sign-in')
  await page.waitForLoadState('networkidle')
  await page.getByLabel('Email').fill(TEST_USER.email)
  await page.getByLabel('Password').fill(TEST_USER.password)
  await page.getByRole('button', { name: /sign in/i }).click()
  await page.waitForURL('/dashboard', { timeout: 15000 })

  await page.context().storageState({ path: authFile })
})
