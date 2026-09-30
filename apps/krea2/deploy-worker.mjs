import { execSync } from 'node:child_process'
import { readFileSync, existsSync, writeFileSync, mkdtempSync, rmSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { tmpdir } from 'node:os'
import { fileURLToPath } from 'node:url'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = join(__dirname, '..')
const workspaceRoot = join(__dirname, '..', '..')
const providerPath = join(workspaceRoot, 'dist', 'apps', 'krea2', 'provider.json')
const schemasPath = join(workspaceRoot, 'apps', 'krea2', 'contracts', 'krea2_ref2img.json')

if (!existsSync(providerPath)) {
  console.error('[deploy-worker] provider.json not found; run krea2 provider deploys first')
  process.exit(1)
}

const providers = JSON.parse(readFileSync(providerPath, 'utf-8'))
const schemas = JSON.parse(readFileSync(schemasPath, 'utf-8'))
const modal = providers.modal || {}
const beam = providers.beam || {}

const tmp = mkdtempSync(join(tmpdir(), 'krea2-router-input-'))
const routerInputPath = join(tmp, 'router-input.json')
try {
  writeFileSync(routerInputPath, JSON.stringify({
    contractName: 'krea2_ref2img',
    input: schemas.input,
    output: schemas.output,
  }, null, 2))
  const deployScript = join(workspaceRoot, 'apps', 'worker-router', 'scripts', 'deploy-worker.mjs')
  execSync(`node "${deployScript}" \\
    --contract-path "${routerInputPath}" \\
    --worker-name "krea2-router-worker" \\
    --provider-type "modal" \\
    --provider-token "" \\
    --provider-api-url "${modal.url || ''}" \\
    --provider-app-name "${modal.app || ''}" \\
    --provider-endpoint-name "" \\
    --beam-api-url "${beam.url || ''}" \\
    --beam-task-api "${beam.taskApi || ''}"`, {
    cwd: root,
    stdio: 'inherit'
  })
} finally {
  rmSync(tmp, { recursive: true, force: true })
}
