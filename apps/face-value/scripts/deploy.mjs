#!/usr/bin/env node
/**
 * Deploy face-value to Vercel.
 * Uses VERCEL_TOKEN env var if set (CI), otherwise uses Vercel CLI auth config (local).
 */

import { execSync } from "node:child_process"

const VERCEL_TOKEN = process.env.VERCEL_TOKEN
const tokenFlag = VERCEL_TOKEN ? `--token=${VERCEL_TOKEN}` : ""
const cmd = `vercel deploy --prod --yes ${tokenFlag}`

console.log(`[deploy] Running: ${cmd}`)
execSync(cmd, { stdio: "inherit" })