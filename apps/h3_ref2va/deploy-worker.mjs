import { execSync } from 'node:child_process'
import { readFileSync, existsSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = join(__dirname, '..')
const contractPath = join(root, 'dist', 'apps', 'h3_ref2va', 'contract.json')

if (!existsSync(contractPath)) {
  process.exit(0)
}

const contract = JSON.parse(readFileSync(contractPath, 'utf-8'))

execSync(`node ../../../worker-router/scripts/deploy-worker.mjs \\
  --contract-path "${contractPath}" \\
  --worker-name "h3-ref2va-router-worker" \\
  --provider-type "beam" \\
  --provider-token "" \\
  --provider-api-url "https://api.beam.cloud" \\
  --provider-app-name "" \\
  --provider-endpoint-name ""`, { cwd: root, stdio: 'inherit' })
