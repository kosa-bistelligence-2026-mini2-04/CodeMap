import { execSync } from 'node:child_process'
import * as path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

const ROOT = path.resolve(__dirname, '..')

export default async function globalTeardown() {
  execSync('docker compose -f docker-compose.test.yml down -v', {
    stdio: 'inherit',
    cwd: ROOT,
  })
}
