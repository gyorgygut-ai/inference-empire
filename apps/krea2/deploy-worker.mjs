import { execSync } from 'node:child_process'
import { readFileSync, existsSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = join(__dirname, '..')
const contractPath = join(root, 'dist', 'apps', 'krea2', 'contract.json')

if (!existsSync(contractPath)) {
  process.exit(0)
}

const contract = JSON.parse(readFileSync(contractPath, 'utf-8'))
const providerAppName = contract.provider?.app || contract.app || ''

execSync(`node ../../../worker-router/scripts/deploy-worker.mjs \\
  --contract-path "${contractPath}" \\
  --worker-name "krea2-router-worker" \\
  --provider-type "modal" \\
  --provider-token "" \\
  --provider-api-url "" \\
  --provider-app-name "${providerAppName}" \\
  --provider-endpoint-name ""`, { cwd: root, stdio: 'inherit' })
