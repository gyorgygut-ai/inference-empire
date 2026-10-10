import { describe, expect, it } from 'vitest'

const ROUTER_URL = process.env.KREA2_ROUTER_URL ?? ''
const ROUTER_TOKEN = process.env.KREA2_ROUTER_TOKEN ?? ''
if (!ROUTER_URL || !ROUTER_TOKEN) {
  throw new Error('KREA2_ROUTER_URL and KREA2_ROUTER_TOKEN env vars are required')
}

async function infer(input: Record<string, unknown>): Promise<Record<string, unknown>> {
  const headers = { Authorization: `Bearer ${ROUTER_TOKEN}` }
  const submitted = await fetch(`${ROUTER_URL}/q`, {
    method: 'POST',
    headers: { ...headers, 'Content-Type': 'application/json' },
    body: JSON.stringify({ input }),
  })
  expect(submitted.status).toBe(200)
  const { task_id } = await submitted.json()

  const deadline = Date.now() + 600_000
  while (Date.now() < deadline) {
    const response = await fetch(`${ROUTER_URL}/sup?id=${task_id}`, { headers })
    expect(response.status).toBe(200)
    const body = await response.json()
    if (body.status === 'COMPLETED') {
      return body.output
    }
    if (body.status === 'FAILED' || body.status === 'CANCELLED') {
      throw new Error(`task ${body.status}`)
    }
    await new Promise((resolve) => setTimeout(resolve, 2_000))
  }
  throw new Error('router task did not complete')
}

describe('krea2 router', () => {
  it('good input returns contract and artifact', async () => {
    const out = await infer({ prompt: 'a red square', seed: 7 })
    const url = (out.artifact as { presigned_url: string }).presigned_url
    expect(url).toBeTruthy()
    const artifact = await fetch(url)
    expect(artifact.status).toBe(200)
    expect((await artifact.arrayBuffer()).byteLength).toBeGreaterThan(0)
  })
})
