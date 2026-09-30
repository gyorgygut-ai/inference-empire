import { readFileSync, writeFileSync, mkdirSync, rmSync } from 'node:fs'
import { join, dirname, resolve } from 'node:path'
import { randomUUID } from 'node:crypto'
import { fileURLToPath } from 'node:url'
import { execSync } from 'node:child_process'
import { tmpdir } from 'node:os'
import { mkdtempSync } from 'node:fs'

const __dirname = dirname(fileURLToPath(import.meta.url))
const routerDir = join(__dirname, '..')
const workspaceRoot = join(__dirname, '..', '..', '..')
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
const beamApiUrl = parseArg('beam-api-url') || ''
const beamTaskApi = parseArg('beam-task-api') || ''

if (!contractPath) throw new Error('--contract-path is required')

const routerInput = JSON.parse(readFileSync(contractPath, 'utf-8'))
const authToken = randomUUID()

const varsLines = [
  `PROVIDER_TYPE = "${providerType}"`,
  `PROVIDER_API_URL = "${providerApiUrl}"`,
  `PROVIDER_TOKEN = "${providerToken}"`,
]
if (providerAppName) varsLines.push(`PROVIDER_APP_NAME = "${providerAppName}"`)
if (providerEndpointName) varsLines.push(`PROVIDER_ENDPOINT_NAME = "${providerEndpointName}"`)
if (beamApiUrl) varsLines.push(`BEAM_API_URL = "${beamApiUrl}"`)
if (beamTaskApi) varsLines.push(`BEAM_TASK_API = "${beamTaskApi}"`)

const wranglerToml = `name = "${workerName}"
compatibility_date = "2026-09-28"
compatibility_flags = []
main = "${join(routerDir, 'src', 'index.ts')}"

[vars]
${varsLines.join('\n')}
`

// Isolated config per invocation: parallel family deploys must not share one wrangler.toml
const cfgDir = mkdtempSync(join(tmpdir(), `${workerName}-wrangler-`))
const tomlPath = join(cfgDir, 'wrangler.toml')
writeFileSync(tomlPath, wranglerToml)
let workerUrl = ''
try {
  const out = execSync(`wrangler deploy --config "${tomlPath}"`, { encoding: 'utf-8', cwd: routerDir })
  process.stdout.write(out)
  const match = out.match(/https:\/\/\S+\.workers\.dev/)
  if (!match) throw new Error('worker URL not found in wrangler output')
  workerUrl = match[0]
  execSync(`wrangler secret put AUTH_TOKEN --config "${tomlPath}"`, { input: authToken, encoding: 'utf-8', cwd: routerDir, stdio: ['pipe', 'inherit', 'inherit'] })
} finally {
  rmSync(cfgDir, { recursive: true, force: true })
}

const flavour = workerName.replace(/-router-worker$/, '')
const distDir = join(workspaceRoot, 'dist', 'apps', flavour)
mkdirSync(distDir, { recursive: true })
writeFileSync(join(distDir, 'contract.json'), JSON.stringify({
  workerName,
  workerUrl,
  contractName: routerInput.contractName || flavour,
  input: routerInput.input,
  output: routerInput.output,
}, null, 2))
writeFileSync(join(distDir, '.router-token'), authToken, 'utf-8')
process.stdout.write(`wrote dist/apps/${flavour}/contract.json (worker: ${workerUrl})\n`)
process.stdout.write(`${flavour.toUpperCase()}_ROUTER_TOKEN=${authToken} (store in env for client builds; will not be shown again)\n`)
