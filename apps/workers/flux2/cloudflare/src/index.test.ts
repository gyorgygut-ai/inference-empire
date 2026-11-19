import { describe, expect, it } from 'vitest'
import worker from './index'
import type { RuntimeEnv } from './env'

const authToken = 'router-flux2-auth-token-that-is-long-enough'

class QueueStub {
  readonly messages: unknown[] = []

  async send(message: unknown): Promise<void> {
    this.messages.push(message)
  }
}

class TaskNamespaceStub {
  readonly records = new Map<string, unknown>()

  idFromName(id: string): string {
    return id
  }

  get(id: string) {
    return {
      fetch: async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
        const request = new Request(input, init)
        if (request.method === 'PUT') {
          this.records.set(id, await request.json())
          return new Response(null, { status: 204 })
        }
        const record = this.records.get(id)
        return record
          ? Response.json(record)
          : Response.json({ error: 'Task not found' }, { status: 404 })
      },
    }
  }
}

describe('Cloudflare FLUX.2 HTTP routes', () => {
  it('does not expose the router-owned /q route', async () => {
    const response = await worker.fetch(
      new Request('https://worker.test/q', { method: 'POST' }),
      { AUTH_TOKEN: authToken } as RuntimeEnv,
      {} as ExecutionContext,
    )

    expect(response.status).toBe(404)
  })

  it('does not expose the router-owned /sup route', async () => {
    const response = await worker.fetch(
      new Request('https://worker.test/sup'),
      { AUTH_TOKEN: authToken } as RuntimeEnv,
      {} as ExecutionContext,
    )

    expect(response.status).toBe(404)
  })

  it('rejects a generate request without the router bearer token', async () => {
    const response = await worker.fetch(
      new Request('https://worker.test/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: 'hello' }),
      }),
      { AUTH_TOKEN: authToken } as RuntimeEnv,
      {} as ExecutionContext,
    )

    expect(response.status).toBe(401)
  })

  it('enqueues valid generate input and records its pending task', async () => {
    const queue = new QueueStub()
    const tasks = new TaskNamespaceStub()
    const response = await worker.fetch(
      new Request('https://worker.test/generate', {
        method: 'POST',
        headers: { Authorization: `Bearer ${authToken}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: 'hello' }),
      }),
      { AUTH_TOKEN: authToken, FLUX2_QUEUE: queue, TASKS: tasks } as unknown as RuntimeEnv,
      {} as ExecutionContext,
    )
    const body = await response.json() as { task_id: string }

    expect({
      status: response.status,
      taskId: body.task_id,
      taskRecord: tasks.records.get(body.task_id),
      queuedMessage: queue.messages[0],
    }).toMatchObject({
      status: 202,
      taskId: expect.stringMatching(/^[\da-f-]{36}$/i),
      taskRecord: { status: 'PENDING' },
      queuedMessage: { taskId: body.task_id, input: { prompt: 'hello' } },
    })
  })
})
