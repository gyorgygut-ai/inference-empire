#!/usr/bin/env node
import { spawnSync } from 'node:child_process'
import { readFileSync, statSync, existsSync } from 'node:fs'
import { join } from 'node:path'

const workspaceRoot = process.env.NX_WORKSPACE_ROOT
const { FLUX2_ROUTER_URL } = process.env
const tokenPath = join(workspaceRoot, 'dist', 'apps', 'flux2', '.router-token')
const startedAt = Date.now()

let token = ''
for (let attempt = 0; attempt < 240 && !token; attempt++) {
  if (existsSync(tokenPath) && statSync(tokenPath).mtimeMs >= startedAt) {
    token = readFileSync(tokenPath, 'utf-8').trim()
  }
  if (!token) {
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
}

if (!FLUX2_ROUTER_URL || !token) {
  process.stderr.write('[serve] FLUX2_ROUTER_URL (dev options.env) and a fresh dist/apps/flux2/.router-token are required\n')
  process.exit(1)
}

const res = spawnSync('npx', ['next', 'dev'], {
  cwd: join(workspaceRoot, 'apps', 'face-value'),
  stdio: 'inherit',
  env: { ...process.env, FLUX2_ROUTER_URL, FLUX2_ROUTER_TOKEN: token }
})
process.exit(res.status)
