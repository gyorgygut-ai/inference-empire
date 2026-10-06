#!/usr/bin/env node
import { spawnSync } from 'node:child_process'
import { readFileSync, statSync, existsSync } from 'node:fs'
import { join } from 'node:path'

const workspaceRoot = process.env.NX_WORKSPACE_ROOT
const { FLUX2_ROUTER_URL, KREA2_ROUTER_URL } = process.env
const startedAt = Date.now()

async function readRouterToken(family) {
  const tokenPath = join(workspaceRoot, 'dist', 'apps', family, '.router-token')
  for (let attempt = 0; attempt < 240; attempt++) {
    if (existsSync(tokenPath) && statSync(tokenPath).mtimeMs >= startedAt) {
      const token = readFileSync(tokenPath, 'utf-8').trim()
      if (token) {
        return token
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  return ''
}

const [FLUX2_ROUTER_TOKEN, KREA2_ROUTER_TOKEN] = await Promise.all([readRouterToken('flux2'), readRouterToken('krea2')])

if (!FLUX2_ROUTER_URL || !FLUX2_ROUTER_TOKEN || !KREA2_ROUTER_URL || !KREA2_ROUTER_TOKEN) {
  console.error('[serve] FLUX2_* / KREA2_* URLs (dev options.env) and fresh dist/apps/*/.router-token are required')
  process.exit(1)
}

const res = spawnSync('npx', ['next', 'dev'], {
  cwd: join(workspaceRoot, 'apps', 'assistant-ui-media'),
  stdio: 'inherit',
  env: { ...process.env, FLUX2_ROUTER_URL, FLUX2_ROUTER_TOKEN, KREA2_ROUTER_URL, KREA2_ROUTER_TOKEN }
})
process.exit(res.status)
