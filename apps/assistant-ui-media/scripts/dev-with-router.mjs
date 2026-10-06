#!/usr/bin/env node
import { readFileSync, existsSync } from "node:fs"
import { join } from "node:path"
import { spawnSync } from "node:child_process"

const workspaceRoot = join(import.meta.dirname, "..", "..")
const contractPath = join(workspaceRoot, "dist", "apps", "flux2", "contract.json")
const tokenPath = join(workspaceRoot, "dist", "apps", "flux2", ".router-token")

if (!existsSync(contractPath) || !existsSync(tokenPath)) {
  console.error("[dev-with-router] flux2 dist files not found; ensure flux2:deploy-worker ran first")
  process.exit(1)
}

const contract = JSON.parse(readFileSync(contractPath, "utf-8"))
const workerUrl = contract.workerUrl || ""
const authToken = readFileSync(tokenPath, "utf-8").trim()

if (!workerUrl || !authToken) {
  console.error("[dev-with-router] empty workerUrl or authToken in flux2 dist")
  process.exit(1)
}

console.log(`[dev-with-router] router: ${workerUrl}`)
const res = spawnSync("npx", ["next", "dev"], {
  cwd: join(workspaceRoot, "apps", "assistant-ui-media"),
  stdio: "inherit",
  env: { ...process.env, FLUX2_ROUTER_URL: workerUrl, FLUX2_ROUTER_TOKEN: authToken },
})
process.exit(res.status ?? 1)