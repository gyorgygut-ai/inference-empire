import { readFileSync, writeFileSync, mkdirSync, unlinkSync } from 'node:fs'
import { join, dirname, resolve } from 'node:path'
import { randomUUID } from 'node:crypto'
import { fileURLToPath } from 'node:url'
import { execSync } from 'node:child_process'

const __dirname = dirname(fileURLToPath(import.meta.url))
const args = process.argv.slice(2)
const parseArg = (key) => {
  const idx = args.indexOf(`--${key}`)
  return idx >= 0 ? args[idx + 1] : undefined
}

const contractPath = resolve(parseArg('contract-path') || '')
const workerName = parseArg('worker-name') || 'worker-router'
const providerType = parseArg('provider-type') || 'modal'
const providerToken = parseArg('provider-token') || ''
const providerApiUrl = parseArg('provider-api-url') || ''
const providerAppName = parseArg('provider-app-name') || ''
const providerEndpointName = parseArg('provider-endpoint-name') || ''

if (!contractPath) throw new Error('--contract-path is required')
if (!providerToken) throw new Error('--provider-token is required')

const contract = JSON.parse(readFileSync(contractPath, 'utf-8'))
const authToken = randomUUID()

const varsLines = [
  `AUTH_TOKEN = "${authToken}"`,
  `PROVIDER_TYPE = "${providerType}"`,
  `PROVIDER_API_URL = "${providerApiUrl}"`,
  `PROVIDER_TOKEN = "${providerToken}"`,
]
if (providerAppName) varsLines.push(`PROVIDER_APP_NAME = "${providerAppName}"`)
if (providerEndpointName) varsLines.push(`PROVIDER_ENDPOINT_NAME = "${providerEndpointName}"`)

const wranglerToml = `name = "${workerName}"
compatibility_date = "2026-09-28"
compatibility_flags = []

[vars]
${varsLines.join('\n')}
`

writeFileSync('wrangler.toml', wranglerToml)
try {
  execSync('wrangler deploy', { stdio: 'inherit', cwd: join(__dirname, '..') })
} finally {
  unlinkSync('wrangler.toml')
}

const distDir = join(__dirname, '..', '..', 'dist', 'apps', workerName.replace(/-router-worker$/, ''))
mkdirSync(distDir, { recursive: true })
writeFileSync(join(distDir, 'contract.json'), JSON.stringify({
  ...contract,
  authToken
}, null, 2))
