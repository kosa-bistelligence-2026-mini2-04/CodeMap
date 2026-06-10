import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',

  globalSetup: './e2e/global-setup.ts',
  globalTeardown: './e2e/global-teardown.ts',

  use: {
    trace: 'on-first-retry',
    reducedMotion: 'reduce',
  },

  webServer: [
    {
      command: 'pnpm --filter @repo/api dev:test',
      url: 'http://localhost:4001/api/auth/ok',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      name: 'API',
    },
    {
      command: 'pnpm --filter @repo/portal dev:test',
      url: 'http://localhost:3100',
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
      name: 'Portal',
    },
  ],

  projects: [
    {
      name: 'portal-setup',
      testMatch: /portal\/setup\.ts/,
      use: {
        baseURL: 'http://localhost:3100',
        ...devices['Desktop Chrome'],
      },
    },
    {
      name: 'portal',
      testDir: './e2e/portal',
      dependencies: ['portal-setup'],
      use: {
        baseURL: 'http://localhost:3100',
        ...devices['Desktop Chrome'],
        storageState: 'e2e/.auth/user.json',
      },
    },
    {
      name: 'backoffice',
      testDir: './e2e/backoffice',
      use: {
        baseURL: 'http://localhost:3001',
        ...devices['Desktop Chrome'],
      },
    },
  ],
})
