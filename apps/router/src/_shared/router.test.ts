import { describe, expect, it } from 'vitest'
import { z } from 'zod'
import { readConfig } from './config'
import { createRouter } from './router'

const api = z.object({
  input: z.object({ prompt: z.string() }),
  output: z.object({ image: z.string() }),
})

const env = { AUTH_TOKEN: 'secret-token-12345678901234567890', WORKER_BEAM_URL: 'http://example.test', BEAM_TOKEN: 'beam' }

describe('createRouter', () => {
  it('rejects unauthenticated requests', async () => {
    const router = createRouter(api, '/flux2', { readConfig })
    const response = await router.fetch(new Request('http://localhost/flux2/q', { method: 'POST', body: JSON.stringify({ input: { prompt: 'hi' } }) }), env)
    expect(response.status).toBe(401)
  })

  it('rejects invalid input', async () => {
    const router = createRouter(api, '/flux2', { readConfig })
    const response = await router.fetch(new Request('http://localhost/flux2/q', { method: 'POST', headers: { Authorization: `Bearer ${env.AUTH_TOKEN}` }, body: JSON.stringify({ input: { prompt: 123 } }) }), env)
    expect(response.status).toBe(400)
  })

  it('serves readiness at the router base path', async () => {
    const router = createRouter(api, '/flux2', { readConfig })
    const response = await router.fetch(new Request('http://localhost/flux2/'), env)
    expect(response.status).toBe(200)
  })

  it('returns 503 when not configured', async () => {
    const router = createRouter(api, '/flux2', { readConfig })
    const response = await router.fetch(new Request('http://localhost/flux2/q', { method: 'POST', headers: { Authorization: 'Bearer x' }, body: JSON.stringify({ input: { prompt: 'hi' } }) }), {})
    expect(response.status).toBe(503)
  })
})
