#!/usr/bin/env node
/**
 * Push flux2 router env vars to Vercel.
 * Reads: dist/apps/flux2/contract.json (workerUrl) + dist/apps/flux2/.router-token (authToken)
 * Upserts: FLUX2_ROUTER_URL and FLUX2_ROUTER_TOKEN to Vercel project.
 * Requires VERCEL_TOKEN (GitHub secret), VERCEL_ORG_ID, VERCEL_PROJECT_ID.
 * Exit 0 if Vercel env vars absent (local dev).
 */

import { readFileSync, existsSync } from "node:fs"
import { join } from "node:path"
import { execSync } from "node:child_process"

const VERCEL_TOKEN = process.env.VERCEL_TOKEN
const VERCEL_ORG_ID = process.env.VERCEL_ORG_ID
const VERCEL_PROJECT_ID = process.env.VERCEL_PROJECT_ID

if (!VERCEL_TOKEN || !VERCEL_ORG_ID || !VERCEL_PROJECT_ID) {
  console.log("[push-router-env] Vercel env vars not set; skipping Vercel push (local dev ok)")
  process.exit(0)
}

const workspaceRoot = process.cwd()
const flux2DistDir = join(workspaceRoot, "dist", "apps", "flux2")
const contractPath = join(flux2DistDir, "contract.json")
const tokenPath = join(flux2DistDir, ".router-token")

if (!existsSync(contractPath) || !existsSync(tokenPath)) {
  console.error("[push-router-env] flux2 dist files not found; ensure flux2:deploy-worker ran first")
  process.exit(1)
}

const contract = JSON.parse(readFileSync(contractPath, "utf-8"))
const authToken = readFileSync(tokenPath, "utf-8").trim()
const workerUrl = contract.workerUrl

if (!workerUrl || !authToken) {
  console.error("[push-router-env] Empty workerUrl or authToken in flux2 dist")
  process.exit(1)
}

const envs = [
  { key: "FLUX2_ROUTER_URL", value: workerUrl },
  { key: "FLUX2_ROUTER_TOKEN", value: authToken },
]

const baseUrl = `https://api.vercel.com`
const headers = {
  Authorization: `Bearer ${VERCEL_TOKEN}`,
  "Content-Type": "application/json",
}

function vercelFetch(path, method = "GET", body = null) {
  const url = `${baseUrl}/v10/projects/${VERCEL_PROJECT_ID}/env${path}`
  const options = { method, headers }
  if (body) {
    options.body = JSON.stringify(body)
  }
  const output = execSync(`curl -s -X ${method} -H "Authorization: Bearer ${VERCEL_TOKEN}" -H "Content-Type: application/json" ${body ? `-d '${JSON.stringify(body)}'` : ""} "${url}"`, { encoding: "utf8" })
  return JSON.parse(output)
}

try {
  // Fetch existing envs
  const { envs: existing = [] } = vercelFetch("")
  const existingMap = new Map(existing.map(e => [e.key, e]))

  for (const env of envs) {
    const existingEnv = existingMap.get(env.key)
    // Delete if exists (to change value/sensitivity)
    if (existingEnv) {
      vercelFetch(`/${existingEnv.id}`, "DELETE")
    }
    // Create new (sensitive: true)
    vercelFetch("", "POST", {
      key: env.key,
      value: env.value,
      type: "encrypted",
      target: ["production", "preview"],
    })
    console.log(`[push-router-env] Upserted ${env.key} → Vercel (production+preview)`)
  }
}
catch (err) {
  console.error("[push-router-env] Failed to push env vars:", err.message)
  process.exit(1)
}