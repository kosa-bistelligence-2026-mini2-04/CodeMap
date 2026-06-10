import { execSync } from 'node:child_process'
import * as path from 'node:path'

const ROOT = path.resolve(__dirname, '../../..')

export default async function jestGlobalTeardown() {
  execSync('docker compose -f docker-compose.test.yml down -v', {
    stdio: 'inherit',
    cwd: ROOT,
  })
}
