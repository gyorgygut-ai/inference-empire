import { execSync } from 'node:child_process'
import { readFileSync, existsSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = join(__dirname, '..')
const contractPath = join(root, 'dist', 'apps', 'h3_comfy', 'contract.json')

if (!existsSync(contractPath)) {
  process.exit(0)
}

const contract = JSON.parse(readFileSync(contractPath, 'utf-8'))

execSync(`node ../../../worker-router/scripts/deploy-worker.mjs \\
  --contract-path "${contractPath}" \\
  --worker-name "h3-comfy-router-worker" \\
  --provider-type "modal" \\
  --provider-token "" \\
  --provider-api-url "" \\
  --provider-app-name "${contract.provider?.app || contract.app || ''}" \\
  --provider-endpoint-name ""`, { cwd: root, stdio: 'inherit' })
