import { execSync } from 'node:child_process'
import * as path from 'node:path'

const TEST_DB_URL = 'postgresql://postgres:postgres@localhost:5433/repo_lens_test'
const ROOT = path.resolve(__dirname, '../../..')

export default async function jestGlobalSetup() {
  execSync('docker compose -f docker-compose.test.yml up -d --wait', {
    stdio: 'inherit',
    cwd: ROOT,
  })

  execSync('pnpm --filter @repo/api exec drizzle-kit migrate', {
    stdio: 'inherit',
    cwd: ROOT,
    env: {
      ...process.env,
      DATABASE_URL: TEST_DB_URL,
    },
  })
}
