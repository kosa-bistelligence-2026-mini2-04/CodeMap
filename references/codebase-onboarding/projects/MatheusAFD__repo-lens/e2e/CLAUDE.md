# CLAUDE.md — E2E Tests (Playwright)

> Full rules and best practices in [`docs/TESTING.md`](../docs/TESTING.md).

## Test Structure

```
e2e/
├── portal/              # Portal tests (baseURL: http://localhost:3000)
│   └── {feature}.spec.ts
└── backoffice/          # Backoffice tests (baseURL: http://localhost:3001)
    └── {feature}.spec.ts
```

## File Naming

- Tests: `kebab-case.spec.ts` (e.g. `sign-in.spec.ts`, `user-profile.spec.ts`)

## Required Patterns

```ts
// ✅ Use accessible locators (getByRole, getByLabel, getByText)
await page.getByRole('button', { name: 'Entrar' }).click()

// ❌ NEVER use fragile selectors
await page.click('.btn-primary')
await page.locator('#submit-btn').click()

// ✅ Use web-first assertions (auto-retry)
await expect(page.getByRole('heading')).toHaveText('Dashboard')

// ❌ NEVER use manual assertions
const text = await page.textContent('h1')
expect(text).toBe('Dashboard')
```

## Running Tests

```bash
# All tests (starts servers automatically)
pnpm test:e2e

# Specific project
pnpm test:e2e:portal
pnpm test:e2e:backoffice

# UI Mode (interactive debugging)
pnpm test:e2e:ui

# Specific test
npx playwright test e2e/portal/sign-in.spec.ts

# With headed browser (see the browser)
npx playwright test --headed

# Show report after failure
npx playwright show-report
```
