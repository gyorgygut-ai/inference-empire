import { describe, expect, it } from 'vitest'
import { z } from 'zod'
import { createRouter } from './router'

const api = z.object({
  input: z.object({ prompt: z.string() }),
  output: z.object({ image: z.string() }),
})

describe('createRouter', () => {
  it('rejects unauthenticated requests', async () => {
    const router = createRouter(api, '/flux2', { readConfig: () => ({ routerToken: 'secret-token-12345678901234567890', beamUrl: 'http://example.test', beamToken: 'beam' }) })
    const response = await router.fetch(new Request('http://localhost/flux2/q', { method: 'POST', body: JSON.stringify({ input: { prompt: 'hi' } }) }));    expect(response.status).toBe(401)
  })

  it('rejects invalid input', async () => {
    const router = createRouter(api, '/flux2', { readConfig: () => ({ routerToken: 'secret-token-12345678901234567890', beamUrl: 'http://example.test', beamToken: 'beam' }) })
    const response = await router.fetch(new Request('http://localhost/flux2/q', { method: 'POST', headers: { Authorization: 'Bearer secret-token-12345678901234567890' }, body: JSON.stringify({ input: { prompt: 123 } }) }));    expect(response.status).toBe(400)
  })

  it('returns 503 when not configured', async () => {
    const router = createRouter(api, '/flux2', { readConfig: () => { throw new Error('missing') } })
    const response = await router.fetch(new Request('http://localhost/flux2/q', { method: 'POST', headers: { Authorization: 'Bearer x' }, body: JSON.stringify({ input: { prompt: 'hi' } }) }));    expect(response.status).toBe(503)
  })
})