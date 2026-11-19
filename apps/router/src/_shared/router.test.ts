import { describe, expect, it } from 'vitest'
import { z } from 'zod'
import { readConfig } from './config'
import { createRouter } from './router'
import { encodeTaskId } from './task-id'

const api = z.object({
  input: z.object({ prompt: z.string() }),
  output: z.object({ image: z.string() }),
})

const env = {
  AUTH_TOKEN: 'secret-token-12345678901234567890',
  WORKER_CLOUDFLARE_URL: 'http://example.test',
}

class CloudflareHttpStub {
  readonly requests: Request[] = []

  constructor(private readonly responses: Response[]) {}

  fetch: typeof fetch = async (input, init) => {
    const request = new Request(input, init)
    this.requests.push(request.clone())
    return this.responses.shift() ?? new Response(null, { status: 500 })
  }
}

describe('createRouter', () => {
  it('rejects unauthenticated requests', async () => {
    const router = createRouter(api, '/flux2', { readConfig, provider: 'cloudflare' })
    const response = await router.fetch(new Request('http://localhost/flux2/q', { method: 'POST', body: JSON.stringify({ input: { prompt: 'hi' } }) }), env)
    expect(response.status).toBe(401)
  })

  it('rejects invalid input', async () => {
    const router = createRouter(api, '/flux2', { readConfig, provider: 'cloudflare' })
    const response = await router.fetch(new Request('http://localhost/flux2/q', { method: 'POST', headers: { Authorization: `Bearer ${env.AUTH_TOKEN}` }, body: JSON.stringify({ input: { prompt: 123 } }) }), env)
    expect(response.status).toBe(400)
  })

  it('serves readiness at the router base path', async () => {
    const router = createRouter(api, '/flux2', { readConfig, provider: 'cloudflare' })
    const response = await router.fetch(new Request('http://localhost/flux2/'), env)
    expect(response.status).toBe(200)
  })

  it('returns 503 when not configured', async () => {
    const router = createRouter(api, '/flux2', { readConfig, provider: 'cloudflare' })
    const response = await router.fetch(new Request('http://localhost/flux2/q', { method: 'POST', headers: { Authorization: 'Bearer x' }, body: JSON.stringify({ input: { prompt: 'hi' } }) }), {})
    expect(response.status).toBe(503)
  })

  it('keeps /q and /sup as router endpoints while delegating to Cloudflare generate and task routes', async () => {
    const output = { image: 'https://artifacts.example/image.png' }
    const upstream = new CloudflareHttpStub([
      Response.json({ task_id: 'cloudflare-task-1' }, { status: 202 }),
      Response.json({ status: 'COMPLETED', output }),
    ])
    const router = createRouter(api, '/flux2', { readConfig, provider: 'cloudflare', fetchImpl: upstream.fetch })
    const authorization = { Authorization: `Bearer ${env.AUTH_TOKEN}` }

    const queued = await router.fetch(new Request('http://localhost/flux2/q', {
      method: 'POST',
      headers: { ...authorization, 'Content-Type': 'application/json' },
      body: JSON.stringify({ input: { prompt: 'hi' } }),
    }), env)
    const taskId = (await queued.json() as { task_id: string }).task_id

    const status = await router.fetch(new Request(`http://localhost/flux2/sup?id=${encodeURIComponent(taskId)}`, {
      headers: authorization,
    }), env)
    const firstRequest = upstream.requests[0]
    const secondRequest = upstream.requests[1]

    expect({
      queuedStatus: queued.status,
      routerTaskId: taskId,
      completed: await status.json(),
      generateRequest: {
        url: firstRequest.url,
        method: firstRequest.method,
        authorization: firstRequest.headers.get('Authorization'),
        body: await firstRequest.json(),
      },
      taskRequest: {
        url: secondRequest.url,
        authorization: secondRequest.headers.get('Authorization'),
      },
    }).toEqual({
      queuedStatus: 200,
      routerTaskId: encodeTaskId('cloudflare', 'cloudflare-task-1'),
      completed: { status: 'COMPLETED', output },
      generateRequest: {
        url: 'http://example.test/generate',
        method: 'POST',
        authorization: `Bearer ${env.AUTH_TOKEN}`,
        body: { prompt: 'hi' },
      },
      taskRequest: {
        url: 'http://example.test/tasks/cloudflare-task-1',
        authorization: `Bearer ${env.AUTH_TOKEN}`,
      },
    })
  })
})
