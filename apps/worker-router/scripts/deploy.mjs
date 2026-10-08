#!/usr/bin/env node
import { readFileSync, writeFileSync, existsSync, readdirSync, mkdirSync, mkdtempSync, rmSync } from 'node:fs'
import { join, dirname, basename } from 'node:path'
import { tmpdir } from 'node:os'
import { randomUUID } from 'node:crypto'
import { execFileSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const routerDir = join(__dirname, '..')
const workspaceRoot = join(__dirname, '..', '..', '..')
const wranglerBin = join(workspaceRoot, 'node_modules', '.bin', 'wrangler')

const args = process.argv.slice(2)
const parseArg = (key) => {
  const idx = args.indexOf(`--${key}`)
  return idx >= 0 ? args[idx + 1] : undefined
}

const project = parseArg('router')
if (!project) {
  console.error('[deploy] --router is required')
  process.exit(1)
}
const family = project.endsWith('-router') ? project.slice(0, -'-router'.length) : project

// A router is always the router of exactly one GPU family: resolve that family's contract.
const contractPath = join(workspaceRoot, 'packages', family, 'contract.json')
if (!existsSync(contractPath)) {
  console.error(`[deploy] contract not found at ${contractPath}`)
  process.exit(1)
}
const contract = JSON.parse(readFileSync(contractPath, 'utf-8'))
const contractName = basename(contractPath, '.json')

// Providers: dynamic entries (beam/flash) from provider.json, static modal identity from the contract.
const providerPath = join(workspaceRoot, 'dist', 'apps', family, 'provider.json')
const dynamicProviders = existsSync(providerPath) ? JSON.parse(readFileSync(providerPath, 'utf-8')) : {}
const providers = { ...dynamicProviders, ...(contract.providers || {}) }

// Resolve the token FIRST for idempotency
const distDir = join(workspaceRoot, 'dist', 'apps', family)
mkdirSync(distDir, { recursive: true })

const existingContractPath = join(distDir, 'contract.json')
let authToken
if (existsSync(existingContractPath)) {
  const existing = JSON.parse(readFileSync(existingContractPath, 'utf-8'))
  if (existing.contractName === contractName && JSON.stringify(existing.input) === JSON.stringify(contract.input)) {
    authToken = readFileSync(join(distDir, '.router-token'), 'utf-8').trim()
  } else {
    authToken = randomUUID()
  }
} else {
  authToken = randomUUID()
}

const workerName = `${family.replace(/_/g, '-')}-router-worker`
const modalProxyKey = process.env.MODAL_PROXY_KEY
const modalProxySecret = process.env.MODAL_PROXY_SECRET
if (!modalProxyKey || !modalProxySecret) {
  console.warn('[deploy] MODAL_PROXY_KEY and MODAL_PROXY_SECRET not set, skipping router deployment')
  process.exit(0)
}
providers.modal = { ...providers.modal, proxyKey: modalProxyKey, proxySecret: modalProxySecret }

const wranglerToml = `name = "${workerName}"
compatibility_date = "2026-09-28"
compatibility_flags = ["nodejs_compat"]
main = "${join(routerDir, 'src', 'index.ts')}"

[vars]
AUTH_TOKEN = "${authToken}"
PROVIDERS = ${JSON.stringify(JSON.stringify(providers))}
`

// Isolated config per invocation: parallel family deploys must not share one wrangler.toml
const cfgDir = mkdtempSync(join(tmpdir(), `${workerName}-wrangler-`))
const tomlPath = join(cfgDir, 'wrangler.toml')
writeFileSync(tomlPath, wranglerToml)

let workerUrl = ''
try {
  const out = execFileSync(wranglerBin, ['deploy', '--config', tomlPath], {
    encoding: 'utf-8',
    cwd: routerDir,
    maxBuffer: 10 * 1024 * 1024
  })
  process.stdout.write(out)
  const match = out.match(/https:\/\/[A-Za-z0-9-]+\.[A-Za-z0-9-]+\.workers\.dev/)
  if (!match) {
    const logPath = join(workspaceRoot, 'dist', `wrangler-output-${workerName}.log`)
    mkdirSync(join(workspaceRoot, 'dist'), { recursive: true })
    writeFileSync(logPath, out, 'utf-8')
    throw new Error(`worker URL not found in wrangler output (full output kept at ${logPath})`)
  }
  workerUrl = match[0]
} finally {
  rmSync(cfgDir, { recursive: true, force: true })
}

writeFileSync(join(distDir, 'contract.json'), JSON.stringify({
  workerName,
  workerUrl,
  contractName,
  input: contract.input,
  output: contract.output
}, null, 2))
writeFileSync(join(distDir, '.router-token'), authToken, 'utf-8')
process.stdout.write(`wrote dist/apps/${family}/contract.json (worker: ${workerUrl})\n`)
process.stdout.write(`${family.toUpperCase()}_ROUTER_TOKEN=${authToken} (store in env for client builds; will not be shown again)\n`)
