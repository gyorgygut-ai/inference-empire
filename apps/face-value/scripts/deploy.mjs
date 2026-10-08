#!/usr/bin/env node
/**
 * Deploy face-value to Vercel. Single supported path: `nx deploy` (local or CI).
 * Git auto-deploys are disabled via apps/face-value/vercel.json
 * (`git.deploymentEnabled: false`).
 *
 * The dashboard project sets Root Directory = apps/face-value, so the CLI must
 * run from the workspace root with no path argument: it then applies Root
 * Directory exactly once. Running from apps/face-value doubles the path
 * (apps/face-value/apps/face-value) and fails.
 *
 * Fresh-clone safe: the project link is bootstrapped from the committed
 * apps/face-value/vercel.project.json template (IDs only, non-secret).
 * VERCEL_PROJECT_ID/VERCEL_ORG_ID env vars override it when set (CI).
 * Only auth is per-machine: VERCEL_TOKEN env var (CI) or `vercel login` (local).
 */

import { execSync, execFileSync } from "node:child_process"
import { existsSync, mkdirSync, copyFileSync, readFileSync, realpathSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"

const appDir = join(dirname(fileURLToPath(import.meta.url)), "..")
const workspaceRoot = join(appDir, "..", "..")

if (realpathSync(process.cwd()) !== realpathSync(workspaceRoot)) {
  process.stderr.write(`[deploy] must run from workspace root (${workspaceRoot}); got ${process.cwd()}\n`)
  process.exit(1)
}

const linkDir = join(appDir, ".vercel")
const linkFile = join(linkDir, "project.json")
if (!existsSync(linkFile)) {
  mkdirSync(linkDir, { recursive: true })
  copyFileSync(join(appDir, "vercel.project.json"), linkFile)
}

const template = JSON.parse(readFileSync(join(appDir, "vercel.project.json"), "utf-8"))
const projectId = process.env.VERCEL_PROJECT_ID || template.projectId
const orgId = process.env.VERCEL_ORG_ID || template.orgId
if (!projectId || !orgId) {
  process.stderr.write("[deploy] no Vercel project identity: template corrupt and VERCEL_PROJECT_ID/VERCEL_ORG_ID unset\n")
  process.exit(1)
}

if (!process.env.VERCEL_TOKEN) {
  try {
    execFileSync("vercel", ["whoami"], { stdio: "ignore" })
  } catch {
    process.stderr.write("[deploy] no Vercel auth: set VERCEL_TOKEN or run `vercel login`\n")
    process.exit(1)
  }
}

const tokenFlag = process.env.VERCEL_TOKEN ? `--token=${process.env.VERCEL_TOKEN}` : ""
execSync(`vercel deploy --prod --yes ${tokenFlag}`, {
  stdio: "inherit",
  cwd: workspaceRoot,
  env: { ...process.env, VERCEL_PROJECT_ID: projectId, VERCEL_ORG_ID: orgId },
})
