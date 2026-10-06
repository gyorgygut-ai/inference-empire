import { readFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { describe, expect, it } from 'vitest'

const ROUTER_URL = 'http://127.0.0.1:8787'
const TOKEN_PATH = join(dirname(fileURLToPath(import.meta.url)), '..', '..', '..', 'dist', 'apps', 'flux2', '.router-token')

async function readToken(): Promise<string> {
  const deadline = Date.now() + 60_000
  while (Date.now() < deadline) {
    try {
      return readFileSync(TOKEN_PATH, 'utf-8').trim()
    } catch {
      await new Promise((resolve) => setTimeout(resolve, 250))
    }
  }
  throw new Error(`router token not emitted at ${TOKEN_PATH}`)
}

async function infer(input: Record<string, unknown>): Promise<Record<string, unknown>> {
  const headers = { Authorization: `Bearer ${await readToken()}` }
  const submitted = await fetch(`${ROUTER_URL}/infer`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ input }),
  })
  expect(submitted.status).toBe(200)
  const { task_id } = await submitted.json()

  const deadline = Date.now() + 600_000
  while (Date.now() < deadline) {
    const response = await fetch(`${ROUTER_URL}/inquire?id=${task_id}`, { headers })
    expect(response.status).toBe(200)
    const body = await response.json()
    if (body.status === 'completed') {
      return body.output
    }
    if (body.status === 'failed' || body.status === 'cancelled') {
      throw new Error(`task ${body.status}`)
    }
    await new Promise((resolve) => setTimeout(resolve, 2_000))
  }
  throw new Error('router task did not complete')
}

describe('flux2 router', () => {
  it('good input returns contract and artifact', async () => {
    const out = await infer({ prompt: 'a red square', seed: 7 })
    const url = (out.artifact as { presigned_url: string }).presigned_url
    expect(url).toBeTruthy()
    const artifact = await fetch(url)
    expect(artifact.status).toBe(200)
    expect((await artifact.arrayBuffer()).byteLength).toBeGreaterThan(0)
  })
})
