import { execSync } from 'node:child_process'
import * as path from 'node:path'
import * as fs from 'node:fs'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

const TEST_DB_URL =
  process.env.DATABASE_URL ?? 'postgresql://postgres:postgres@localhost:5433/repo_lens_test'
const ROOT = path.resolve(__dirname, '..')
const IS_CI = !!process.env.CI

export default async function globalSetup() {
  if (!IS_CI) {
    execSync('docker compose -f docker-compose.test.yml up -d --wait', {
      stdio: 'inherit',
      cwd: ROOT,
    })
  }

  const authDir = path.join(__dirname, '.auth')
  if (!fs.existsSync(authDir)) {
    fs.mkdirSync(authDir, { recursive: true })
  }

  execSync('pnpm --filter @repo/api exec drizzle-kit migrate', {
    stdio: 'inherit',
    cwd: ROOT,
    env: {
      ...process.env,
      DATABASE_URL: TEST_DB_URL,
    },
  })
}
