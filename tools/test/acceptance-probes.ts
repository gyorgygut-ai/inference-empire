import { execFileSync } from 'node:child_process'
import { resolve } from 'node:path'
import { expect } from 'vitest'
import { z } from 'zod'
import { inferWithPolling } from '../../packages/task-queue-client/src/client'
import { api as flux2 } from '../../packages/schemas/workers/flux2.schema'
import { api as tinysd } from '../../packages/schemas/workers/tiny_sd.schema'

const workspace = resolve(import.meta.dirname, '../..')
const contracts = { flux2, tinysd }
export const inferenceTimeout = 15 * 60 * 1000

export function deployedUrl(provider: 'beam' | 'cf-worker' | 'vercel', ...args: string[]) {
  return z.url().parse(execFileSync('npx', ['tsx', `tools/get-${provider}-url.ts`, ...args], {
    cwd: workspace, encoding: 'utf8', timeout: 60000,
  }).trim())
}

export async function pingWorker(project: string, token: string) {
  const response = await fetch(deployedUrl('beam', project), {
    method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ prompt: 'a red square', seed: 7 }), signal: AbortSignal.timeout(60000),
  })
  expect(response.ok, `${project} queue HTTP ${response.status}`).toBe(true)
  expect(z.object({ task_id: z.string().min(1) }).safeParse(await response.json()).success).toBe(true)
}

export async function generateImage(model: keyof typeof contracts, baseUrl: string, token: string) {
  const input = contracts[model].shape.input.parse({ prompt: 'a portrait of a woman', seed: 7 })
  const result = await inferWithPolling<typeof input, unknown>(input, {
    baseUrl, token, pollIntervalMs: 2000, timeoutMs: inferenceTimeout,
  }, fetch, AbortSignal.timeout(inferenceTimeout))
  return contracts[model].shape.output.parse(result).artifact.presigned_url
}

export async function expectImage(url: string) {
  const response = await fetch(z.url().parse(url), { signal: AbortSignal.timeout(60000) })
  expect(response.ok, `artifact HTTP ${response.status}`).toBe(true)
  expect(response.headers.get('content-type')).toMatch(/^image\//)
  expect((await response.arrayBuffer()).byteLength).toBeGreaterThan(0)
}

export async function queueWithToken(baseUrl: string, token: string) {
  return fetch(`${baseUrl}/q`, {
    method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ input: { prompt: 'a red square', seed: 7 } }), signal: AbortSignal.timeout(30000),
  })
}

export async function pingRouter(baseUrl: string, token: string) {
  const response = await fetch(`${baseUrl}/sup`, {
    headers: { Authorization: `Bearer ${token}` }, signal: AbortSignal.timeout(30000),
  })
  expect(response.status).toBe(400)
  expect(await response.json()).toEqual({ error: 'Missing task id' })
}

export async function pingFrontend(url: string) {
  const response = await fetch(url, { signal: AbortSignal.timeout(60000) })
  expect(response.ok).toBe(true)
  expect(response.headers.get('content-type')).toContain('text/html')
  expect(await response.text()).toMatch(/<!doctype html>/i)
}
