#!/usr/bin/env node
import { readFileSync, existsSync } from "node:fs"
import { join } from "node:path"
import { spawnSync } from "node:child_process"

const workspaceRoot = join(import.meta.dirname, "..", "..")
const descriptorPath = join(workspaceRoot, "dist", "apps", "flux2", ".router.local.json")

function readDescriptor(path, waitMs) {
  const deadline = Date.now() + waitMs
  while (!existsSync(path)) {
    if (Date.now() > deadline) {
      console.error(`[dev-with-router] ${path} not found; ensure flux2:serve-router is running`)
      process.exit(1)
    }
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 250)
  }
  return JSON.parse(readFileSync(path, "utf-8"))
}

const { url, token } = readDescriptor(descriptorPath, 30000)
console.log(`[dev-with-router] local flux2 router: ${url}`)
const res = spawnSync("npx", ["next", "dev"], {
  cwd: join(workspaceRoot, "apps", "face-value"),
  stdio: "inherit",
  env: { ...process.env, FLUX2_ROUTER_URL: url, FLUX2_ROUTER_TOKEN: token },
})
process.exit(res.status)
