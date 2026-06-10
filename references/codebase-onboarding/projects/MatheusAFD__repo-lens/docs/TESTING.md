# Testing — E2E Tests Guide with Playwright

## Overview

The monorepo uses **Playwright** for E2E tests of the frontend (Portal). The configuration is at the project root in `playwright.config.ts` with three projects: `portal-setup`, `portal`, and `backoffice` (reserved for future use).

| Project | App | Base URL | Test Directory |
|---|---|---|---|
| `portal-setup` | `apps/portal` | `http://localhost:3100` | `e2e/portal/setup.ts` |
| `portal` | `apps/portal` | `http://localhost:3100` | `e2e/portal/` |

Both dev servers (API in test mode and Portal in test mode) are started automatically via Playwright's `webServer`.

---

## Directory Structure

```
e2e/
├── CLAUDE.md
├── global-setup.ts
├── global-teardown.ts
├── helpers/
├── .auth/
│   └── user.json          # Auth state saved by portal-setup
└── portal/
    ├── setup.ts            # Creates the authenticated session (runs before portal)
    ├── sign-in.spec.ts
    ├── dashboard.spec.ts
    ├── repos.spec.ts
    ├── analysis.spec.ts
    ├── analysis-questions.spec.ts
    └── {feature}.spec.ts
```

### Naming

- Test files: `kebab-case.spec.ts` (e.g. `sign-in.spec.ts`, `analysis.spec.ts`)
- Name files after the feature being tested

---

## Commands

```bash
# Run all E2E tests
pnpm test:e2e

# Run portal tests only
pnpm test:e2e:portal

# UI Mode — interactive debugging with time travel
pnpm test:e2e:ui

# Run a specific test file
npx playwright test e2e/portal/sign-in.spec.ts

# Run with visible browser
npx playwright test --headed

# View HTML report after run
npx playwright show-report

# Run in debug mode (step by step)
npx playwright test --debug
```

---

## Test Mode Ports

Apps run on different ports than normal development to avoid conflicts:

| App | Dev Port | Test Port |
|---|---|---|
| `apps/api` | 4000 | 4001 |
| `apps/portal` | 3000 | 3100 |

The `dev:test` command in each app configures these ports via environment variables.

---

## Authentication in Tests

The project uses Playwright's **stored auth state**. The `portal-setup` project runs first and saves the authenticated session to `e2e/.auth/user.json`. All `portal` project tests reuse this session via `storageState`.

```ts
// e2e/portal/setup.ts — pattern example
import { test as setup } from '@playwright/test'

setup('authenticate', async ({ page }) => {
  await page.goto('/auth/sign-in')
  // ...perform login...
  await page.context().storageState({ path: 'e2e/.auth/user.json' })
})
```

Each test does not need to log in manually — the session is already available.

---

## Writing Tests

### Basic structure

```ts
import { test, expect } from '@playwright/test'

test.describe('Sign In', () => {
  test('should sign in with valid credentials', async ({ page }) => {
    await page.goto('/auth/sign-in')

    await page.getByLabel('Email').fill('user@example.com')
    await page.getByLabel('Password').fill('password123')
    await page.getByRole('button', { name: 'Sign In' }).click()

    await expect(page).toHaveURL('/dashboard')
    await expect(page.getByRole('heading')).toHaveText('Dashboard')
  })

  test('should show error for invalid credentials', async ({ page }) => {
    await page.goto('/auth/sign-in')

    await page.getByLabel('Email').fill('wrong@example.com')
    await page.getByLabel('Password').fill('wrongpassword')
    await page.getByRole('button', { name: 'Sign In' }).click()

    await expect(page.getByText('Invalid credentials')).toBeVisible()
  })
})
```

---

## Best Practices

### 1. Use accessible locators

Prefer locators that reflect how the user interacts with the page:

```ts
// ✅ Correct — accessible locators (resilient to UI changes)
page.getByRole('button', { name: 'Save' })
page.getByLabel('Email')
page.getByText('Welcome')
page.getByPlaceholder('Enter your name')
page.getByTestId('user-avatar')  // when there is no accessible alternative

// ❌ Incorrect — fragile selectors
page.locator('.btn-primary')
page.locator('#submit-btn')
page.locator('div > form > button:nth-child(2)')
```

**Preference order:**
1. `getByRole()` — buttons, links, headings, inputs
2. `getByLabel()` — form fields
3. `getByText()` — visible text
4. `getByPlaceholder()` — inputs with placeholder
5. `getByTestId()` — last resort, add `data-testid` to the component

### 2. Use web-first assertions

Playwright assertions auto-retry until timeout. Never extract values manually.

```ts
// ✅ Web-first assertions (auto-retry, async)
await expect(page.getByRole('heading')).toHaveText('Dashboard')
await expect(page.getByRole('button')).toBeEnabled()
await expect(page).toHaveURL('/dashboard')
await expect(page.getByText('Loading')).not.toBeVisible()

// ❌ Manual assertions (no retry, flaky)
const text = await page.textContent('h1')
expect(text).toBe('Dashboard')
```

### 3. Isolate tests

Each test must be independent. Do not depend on state left by previous tests.

### 4. Use `test.describe` to group

```ts
test.describe('User Profile', () => {
  test.describe('when authenticated', () => {
    test('should display user info', async ({ page }) => { /* ... */ })
    test('should allow editing name', async ({ page }) => { /* ... */ })
  })

  test.describe('when not authenticated', () => {
    test('should redirect to sign-in', async ({ page }) => { /* ... */ })
  })
})
```

### 5. Avoid `waitForTimeout`

Never use fixed waits. Use locators and assertions that auto-retry.

```ts
// ✅ Smart wait via assertion
await expect(page.getByRole('table')).toBeVisible()

// ✅ Wait for navigation
await page.waitForURL('/dashboard')

// ❌ Fixed wait (flaky, slow)
await page.waitForTimeout(3000)
```

---

## Advanced Patterns

### Intercept and mock API

```ts
test('should display repos from API', async ({ page }) => {
  await page.route('**/api/repos', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        { id: '1', fullName: 'owner/repo', stars: 42 },
      ]),
    }),
  )

  await page.goto('/repos')
  await expect(page.getByText('owner/repo')).toBeVisible()
})
```

### Test navigation and redirects

```ts
test('should redirect unauthenticated user to sign-in', async ({ page }) => {
  await page.goto('/dashboard')
  await expect(page).toHaveURL(/\/auth\/sign-in/)
})
```

### Test forms with validation

```ts
test('should validate required fields', async ({ page }) => {
  await page.goto('/auth/sign-up')

  await page.getByRole('button', { name: 'Create Account' }).click()

  await expect(page.getByText('Email is required')).toBeVisible()
  await expect(page.getByText('Password is required')).toBeVisible()
})
```

---

## Debugging

### UI Mode

The most powerful mode for debugging. Allows seeing the test run, inspecting the DOM, and time-traveling between steps.

```bash
pnpm test:e2e:ui
```

### Headed Mode

See the browser during execution:

```bash
npx playwright test --headed
```

### Debug Mode

Pause at each step and inspect:

```bash
npx playwright test --debug
```

### Trace Viewer

After a failure, Playwright generates traces automatically (in CI with retries). To open:

```bash
npx playwright show-report
```

### Add pause in code

```ts
test('debug this', async ({ page }) => {
  await page.goto('/')
  await page.pause()  // Opens the Playwright Inspector
  // ...
})
```

---

## Configuration

The configuration is in `playwright.config.ts` at the monorepo root. Key options:

| Option | Value | Description |
|---|---|---|
| `fullyParallel` | `true` | Tests run in parallel |
| `forbidOnly` | `!!process.env.CI` | Fails if `.only` is present in CI |
| `retries` | `2` in CI, `0` local | Automatic retries |
| `workers` | `1` in CI, auto local | Number of parallel workers |
| `reporter` | `'html'` | HTML report |

### Web Servers

Playwright automatically starts 2 servers before the tests:

1. **API** (`@repo/api dev:test`) — `http://localhost:4001`
2. **Portal** (`@repo/portal dev:test`) — `http://localhost:3100`

In local development, if the servers are already running, Playwright reuses them (`reuseExistingServer: true`).

---

## References

- [Playwright — Getting Started](https://playwright.dev/docs/intro)
- [Playwright — Best Practices](https://playwright.dev/docs/best-practices)
- [Playwright — Locators](https://playwright.dev/docs/locators)
- [Playwright — Assertions](https://playwright.dev/docs/test-assertions)
- [Playwright — Web Server](https://playwright.dev/docs/test-webserver)
- [Playwright — Test Configuration](https://playwright.dev/docs/test-configuration)
