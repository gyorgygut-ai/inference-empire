#!/usr/bin/env node
import { spawnSync } from 'node:child_process'
import { join } from 'node:path'

const workspaceRoot = process.env.NX_WORKSPACE_ROOT
const { FLUX2_ROUTER_URL, FLUX2_ROUTER_TOKEN } = process.env
if (!FLUX2_ROUTER_URL || !FLUX2_ROUTER_TOKEN) {
  console.error('[serve] FLUX2_ROUTER_URL / FLUX2_ROUTER_TOKEN must be provided by Nx (dev options.env)')
  process.exit(1)
}

const res = spawnSync('npx', ['next', 'dev'], {
  cwd: join(workspaceRoot, 'apps', 'face-value'),
  stdio: 'inherit',
  env: { ...process.env, FLUX2_ROUTER_URL, FLUX2_ROUTER_TOKEN }
})
process.exit(res.status)
