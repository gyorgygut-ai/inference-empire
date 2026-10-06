#!/usr/bin/env node
import { readFileSync, existsSync } from "node:fs"
import { join } from "node:path"
import { spawnSync } from "node:child_process"

const workspaceRoot = join(import.meta.dirname, "..", "..")
const flux2Descriptor = join(workspaceRoot, "dist", "apps", "flux2", ".router.local.json")
const krea2Descriptor = join(workspaceRoot, "dist", "apps", "krea2", ".router.local.json")

function readDescriptor(path, waitMs) {
  const deadline = Date.now() + waitMs
  while (!existsSync(path)) {
    if (Date.now() > deadline) {
      console.error(`[dev-with-router] ${path} not found; ensure the matching serve-router is running`)
      process.exit(1)
    }
    Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 250)
  }
  return JSON.parse(readFileSync(path, "utf-8"))
}

const flux2 = readDescriptor(flux2Descriptor, 30000)
const krea2 = readDescriptor(krea2Descriptor, 30000)
console.log(`[dev-with-router] local flux2 router: ${flux2.url}`)
console.log(`[dev-with-router] local krea2 router: ${krea2.url}`)
const res = spawnSync("npx", ["next", "dev"], {
  cwd: join(workspaceRoot, "apps", "assistant-ui-media"),
  stdio: "inherit",
  env: {
    ...process.env,
    FLUX2_ROUTER_URL: flux2.url,
    FLUX2_ROUTER_TOKEN: flux2.token,
    KREA2_ROUTER_URL: krea2.url,
    KREA2_ROUTER_TOKEN: krea2.token,
  },
})
process.exit(res.status)
