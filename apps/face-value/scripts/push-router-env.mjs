#!/usr/bin/env node
/**
 * Push flux2 router env vars to Vercel.
 * Reads: dist/apps/flux2/contract.json (workerUrl) + dist/apps/flux2/.router-token (authToken)
 * Upserts: FLUX2_ROUTER_URL and FLUX2_ROUTER_TOKEN to Vercel project.
 * Requires VERCEL_TOKEN (GitHub secret), VERCEL_ORG_ID, VERCEL_PROJECT_ID.
 * Exit 0 if Vercel env vars absent (local dev).
 */

import { readFileSync, writeFileSync, existsSync } from "node:fs"
import { join } from "node:path"
import { execSync } from "node:child_process"

const workspaceRoot = process.cwd()
const projectRoot = join(workspaceRoot, "apps", "face-value")

// Read VERCEL_TOKEN from env vars or Vercel CLI auth config
let VERCEL_TOKEN = process.env.VERCEL_TOKEN
if (!VERCEL_TOKEN) {
  const authPath = process.platform === "darwin"
    ? join(process.env.HOME, "Library", "Application Support", "com.vercel.cli", "auth.json")
    : join(process.env.HOME, ".vercel", "auth.json")
  if (existsSync(authPath)) {
    try {
      const authConfig = JSON.parse(readFileSync(authPath, "utf-8"))
      VERCEL_TOKEN = authConfig.token
    }
    catch { /* ignore */ }
  }
}

if (!VERCEL_TOKEN) {
  console.log("[push-router-env] VERCEL_TOKEN not found; skipping Vercel push (local dev ok)")
  process.exit(0)
}

// Read VERCEL_PROJECT_ID from env vars or .vercel/project.json
let VERCEL_PROJECT_ID = process.env.VERCEL_PROJECT_ID
if (!VERCEL_PROJECT_ID) {
  const projectJsonPath = join(projectRoot, ".vercel", "project.json")
  if (existsSync(projectJsonPath)) {
    const projectJson = JSON.parse(readFileSync(projectJsonPath, "utf-8"))
    VERCEL_PROJECT_ID = projectJson.projectId
  }
}

if (!VERCEL_PROJECT_ID) {
  console.log("[push-router-env] VERCEL_PROJECT_ID not found; skipping Vercel push (local dev ok)")
  process.exit(0)
}
const flux2DistDir = join(workspaceRoot, "dist", "apps", "flux2")
const contractPath = join(flux2DistDir, "contract.json")
const tokenPath = join(flux2DistDir, ".router-token")

if (!existsSync(contractPath) || !existsSync(tokenPath)) {
  console.error("[push-router-env] flux2 dist files not found; ensure worker-router:flux2-deploy ran first")
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

const syncedTokenPath = join(flux2DistDir, '.vercel-synced-token')
const syncedToken = existsSync(syncedTokenPath) ? readFileSync(syncedTokenPath, 'utf-8').trim() : null

if (syncedToken === authToken) {
  console.log(`[push-router-env] Env vars already synced for current router token; skipping Vercel push`)
  process.exit(0)
}

try {
  const { envs: existing = [] } = vercelFetch("")
  const existingMap = new Map(existing.map(e => [e.key, e]))

  for (const env of envs) {
    const existingEnv = existingMap.get(env.key)
    if (existingEnv) {
      vercelFetch(`/${existingEnv.id}`, "DELETE")
    }
    vercelFetch("", "POST", {
      key: env.key,
      value: env.value,
      type: "encrypted",
      target: ["production", "preview"],
    })
    console.log(`[push-router-env] Upserted ${env.key} → Vercel (production+preview)`)
  }
  writeFileSync(syncedTokenPath, authToken, 'utf-8')
}
catch (err) {
  console.error("[push-router-env] Failed to push env vars:", err.message)
  process.exit(1)
}