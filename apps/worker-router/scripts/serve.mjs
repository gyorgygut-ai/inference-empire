#!/usr/bin/env node
import { readFileSync, existsSync, writeFileSync, readdirSync, mkdtempSync, rmSync, mkdirSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { tmpdir } from 'node:os'
import { spawn } from 'node:child_process'
import { fileURLToPath } from 'node:url'
import { randomUUID } from 'node:crypto'

const __dirname = dirname(fileURLToPath(import.meta.url))
const workspaceRoot = join(__dirname, '..', '..', '..')
const routerEntry = join(workspaceRoot, 'apps', 'worker-router', 'src', 'index.ts')
const wranglerBin = join(workspaceRoot, 'node_modules', '.bin', 'wrangler')

const PORTS = { flux2: 8787, krea2: 8788 }
const INSPECTOR_PORTS = { flux2: 9229, krea2: 9230 }

const args = process.argv.slice(2)
const project = args[args.indexOf('--router') + 1]
if (!project) {
  console.error('[serve] --router is required')
  process.exit(1)
}
const family = project.endsWith('-router') ? project.slice(0, -'-router'.length) : project
if (!PORTS[family]) {
  console.error(`[serve] no local port for family: ${family}`)
  process.exit(1)
}

const authToken = randomUUID()

const distDir = join(workspaceRoot, 'dist', 'apps', family)
mkdirSync(distDir, { recursive: true })
const tokenPath = join(distDir, '.router-token')
rmSync(tokenPath, { force: true })

// Providers: static modal identity from the contract, dynamic entries (beam/flash) from provider.json when present.
const contractsDir = join(workspaceRoot, 'apps', family, 'contracts')
const contractFiles = readdirSync(contractsDir).filter((file) => file.endsWith('.json'))
if (contractFiles.length !== 1) {
  console.error(`[serve] expected exactly one contract in ${contractsDir}, found ${contractFiles.length}`)
  process.exit(1)
}
const contract = JSON.parse(readFileSync(join(contractsDir, contractFiles[0]), 'utf-8'))
const providerPath = join(workspaceRoot, 'dist', 'apps', family, 'provider.json')
const dynamicProviders = existsSync(providerPath) ? JSON.parse(readFileSync(providerPath, 'utf-8')) : {}
const providers = { ...dynamicProviders, ...(contract.providers || {}) }

// The Worker authenticates to the Modal bridge with a Modal proxy token (wk-/ws- pair).
const modalProxyKey = process.env.MODAL_PROXY_KEY
const modalProxySecret = process.env.MODAL_PROXY_SECRET
if (!modalProxyKey || !modalProxySecret) {
  console.error('[serve] MODAL_PROXY_KEY and MODAL_PROXY_SECRET must be set')
  process.exit(1)
}
providers.modal = { ...providers.modal, proxyKey: modalProxyKey, proxySecret: modalProxySecret }

const cfgDir = mkdtempSync(join(tmpdir(), `${family}-serve-`))
const cfgPath = join(cfgDir, 'wrangler.toml')
writeFileSync(cfgPath, `name = "${family}-router-dev"
compatibility_date = "2026-09-28"
compatibility_flags = ["nodejs_compat"]
main = "${routerEntry}"

[vars]
AUTH_TOKEN = "${authToken}"
PROVIDERS = ${JSON.stringify(JSON.stringify(providers))}
`)

async function portInUse(port) {
  try {
    await fetch(`http://127.0.0.1:${port}/infer`, { method: 'POST' })
    return true
  } catch {
    return false
  }
}

if (await portInUse(PORTS[family])) {
  console.error(`[serve] port ${PORTS[family]} already in use`)
  process.exit(1)
}

const child = spawn(wranglerBin, ['dev', '--config', cfgPath, '--ip', '127.0.0.1', '--port', String(PORTS[family]), '--inspector-port', String(INSPECTOR_PORTS[family]), '--persist-to', join(cfgDir, 'state')], {
  cwd: join(workspaceRoot, 'apps', 'worker-router'),
  stdio: 'inherit'
})

// Emit the token only once wrangler answers: readers of the token go straight to the
// router, so the file appearing must mean the server is accepting connections.
async function waitForReady() {
  const url = `http://127.0.0.1:${PORTS[family]}/infer`
  for (let attempt = 0; attempt < 240; attempt++) {
    try {
      await fetch(url, { method: 'POST' })
      return true
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 250))
    }
  }
  return false
}

waitForReady().then((ready) => {
  if (!ready) {
    console.error('[serve] wrangler did not become ready')
    return
  }
  writeFileSync(tokenPath, authToken, 'utf-8')
  process.stdout.write(`${family.toUpperCase()}_ROUTER_TOKEN=${authToken}\n`)
})

function cleanup() {
  rmSync(cfgDir, { recursive: true, force: true })
}
for (const signal of ['SIGINT', 'SIGTERM']) {
  process.on(signal, () => child.kill(signal))
}
child.on('exit', (code) => {
  cleanup()
  process.exit(code ?? 0)
})
