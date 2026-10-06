#!/usr/bin/env node
import { randomUUID } from "node:crypto"
import { readFileSync, existsSync, writeFileSync, mkdirSync, mkdtempSync, rmSync } from "node:fs"
import { join, dirname } from "node:path"
import { tmpdir } from "node:os"
import { spawnSync } from "node:child_process"
import { fileURLToPath } from "node:url"

const __dirname = dirname(fileURLToPath(import.meta.url))
const workspaceRoot = join(__dirname, "..", "..")
const routerDir = join(workspaceRoot, "apps", "worker-router")
const wranglerBin = join(routerDir, "node_modules", ".bin", "wrangler")
const providerPath = join(workspaceRoot, "dist", "apps", "flux2", "provider.json")
const descriptorPath = join(workspaceRoot, "dist", "apps", "flux2", ".router.local.json")

const WORKER_NAME = "flux2-router-worker"
const PORT = 8787
const AUTH_TOKEN = randomUUID()

if (!existsSync(providerPath)) {
  console.error("[serve-router] provider.json not found; run flux2 provider deploys first")
  process.exit(1)
}

const providers = JSON.parse(readFileSync(providerPath, "utf-8"))
const varsLines = [
  `AUTH_TOKEN = "${AUTH_TOKEN}"`,
  `PROVIDER_TYPE = "modal"`,
  `PROVIDER_API_URL = "${providers.modal.url}"`,
  `PROVIDER_TOKEN = ""`,
  `PROVIDER_APP_NAME = "${providers.modal.app}"`,
  `BEAM_API_URL = "${providers.beam.url}"`,
  `BEAM_TASK_API = "${providers.beam.taskApi}"`,
]

const wranglerToml = `name = "${WORKER_NAME}"
compatibility_date = "2026-09-28"
compatibility_flags = []
main = "${join(routerDir, "src", "index.ts")}"

[vars]
${varsLines.join("\n")}
`

const cfgDir = mkdtempSync(join(tmpdir(), `${WORKER_NAME}-wrangler-dev-`))
const tomlPath = join(cfgDir, "wrangler.toml")
writeFileSync(tomlPath, wranglerToml)

const url = `http://127.0.0.1:${PORT}`
mkdirSync(join(workspaceRoot, "dist", "apps", "flux2"), { recursive: true })
writeFileSync(descriptorPath, JSON.stringify({ url, token: AUTH_TOKEN }, null, 2))
console.log(`[serve-router] flux2 router on ${url}`)

let exitCode = 0
try {
  const res = spawnSync(wranglerBin, ["dev", "--config", tomlPath, "--port", String(PORT), "--ip", "127.0.0.1"], {
    cwd: routerDir,
    stdio: "inherit",
  })
  exitCode = res.status
} finally {
  rmSync(cfgDir, { recursive: true, force: true })
}
process.exit(exitCode)
