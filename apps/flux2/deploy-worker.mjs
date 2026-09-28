import { execSync } from 'node:child_process'
import { readFileSync, existsSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = join(__dirname, '..')
const contractPath = join(root, 'dist', 'apps', 'flux2', 'contract.json')

if (!existsSync(contractPath)) {
  console.log('[deploy-worker] contract.json not found, skipping (provider deploy has not run yet)')
  process.exit(0)
}

const contract = JSON.parse(readFileSync(contractPath, 'utf-8'))

const providerType = contract.provider?.type || 'modal'
const providerApiUrl = contract.provider?.apiUrl || contract.provider?.url || ''
const providerAppName = contract.provider?.app || contract.app || ''
const providerEndpointName = contract.provider?.endpointId || contract.endpointId || ''

execSync(`node ../../../worker-router/scripts/deploy-worker.mjs \\
  --contract-path "${contractPath}" \\
  --worker-name "flux2-router-worker" \\
  --provider-type "${providerType}" \\
  --provider-token "" \\
  --provider-api-url "${providerApiUrl}" \\
  --provider-app-name "${providerAppName}" \\
  --provider-endpoint-name "${providerEndpointName}"`, {
  cwd: root,
  stdio: 'inherit'
})
