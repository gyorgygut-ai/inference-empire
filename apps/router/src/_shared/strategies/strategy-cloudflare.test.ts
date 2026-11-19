import { describe, expect, it } from 'vitest'
import type { RuntimeConfig } from '../config'
import { strategyCloudflare } from './strategy-cloudflare'

const config: RuntimeConfig = {
  routerToken: 'router-token',
  cloudflareUrl: 'https://worker-flux2-cloudflare.example.workers.dev',
}

class WorkerHttpStub {
  readonly requests: Request[] = []

  constructor(private readonly responses: Response[]) {}

  fetch: typeof fetch = async (input, init) => {
    const request = new Request(input, init)
    this.requests.push(request.clone())
    return this.responses.shift() ?? new Response(null, { status: 500 })
  }
}

describe('strategyCloudflare', () => {
  it('submits input to generate using the router token and returns the worker task id', async () => {
    const upstream = new WorkerHttpStub([Response.json({ task_id: 'task-123' }, { status: 202 })])
    const strategy = strategyCloudflare(config, upstream.fetch)
    const input = { prompt: 'mountain lake' }
    const result = await strategy.pushToTaskQueue(input)
    const request = upstream.requests[0]

    expect({
      result,
      url: request.url,
      method: request.method,
      authorization: request.headers.get('Authorization'),
      input: await request.json(),
    }).toEqual({
      result: { task_id: 'task-123' },
      url: `${config.cloudflareUrl}/generate`,
      method: 'POST',
      authorization: 'Bearer router-token',
      input,
    })
  })

  it('retrieves completed task output and preserves the artifact URL', async () => {
    const output = { artifact: { presigned_url: 'https://artifacts.example/image.png' } }
    const upstream = new WorkerHttpStub([Response.json({ status: 'COMPLETED', output })])
    const strategy = strategyCloudflare(config, upstream.fetch)
    const result = await strategy.fetchTaskStatus('task/123')
    const request = upstream.requests[0]

    expect({
      result,
      url: request.url,
      authorization: request.headers.get('Authorization'),
    }).toEqual({
      result: { status: 'COMPLETED', output },
      url: `${config.cloudflareUrl}/tasks/task%2F123`,
      authorization: 'Bearer router-token',
    })
  })

  it('surfaces an upstream authorization failure', async () => {
    const strategy = strategyCloudflare(config, new WorkerHttpStub([new Response(null, { status: 401 })]).fetch)

    await expect(strategy.pushToTaskQueue({ prompt: 'invalid token' })).rejects.toThrow('Cloudflare generate returned 401')
  })
})
