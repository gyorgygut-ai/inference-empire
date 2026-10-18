import { Router } from 'itty-router'
import { z } from 'zod'
import { api } from './schema.js'
import type { Env } from '../env.schema.js'
import createProvider, { decodeProviderName, isProviderName } from './providers/create-provider.js'
import { pickTaskHandler } from './pick-task-handler.js'
import type { TaskQueueApi } from './task-queue-api.js'

type Schema = TaskQueueApi<z.infer<typeof api>['input'], z.infer<typeof api>['output']>

const addToQueueRequest = z.object({ input: api.shape.input })

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' }
  })
}

export function createRouter() {
  const router = Router()

  router.all('*', async (request: Request, env: Env) => {
    const authHeader = request.headers.get('Authorization')
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return json({ error: 'Unauthorized' }, 401)
    }
    if (authHeader.substring(7) !== env.ROUTER_AUTH_TOKEN) {
      return json({ error: 'Invalid token' }, 401)
    }
  })

  router.post('/q', async (request: Request, env: Env) => {
    const parsed = addToQueueRequest.safeParse(await request.json())
    if (!parsed.success) {
      return json({ error: 'Invalid body' }, 400)
    }
    const name = pickTaskHandler()
    const provider = createProvider(name)
    const config = provider.resolveConfig(env)
    if (!config) {
      return json({ error: `${name} worker not configured` }, 503)
    }
    const { task_id } = await provider.pushToTaskQueue(parsed.data.input, config)
    const response: Schema['AddToQueueResponse'] = { task_id: provider.encodeTaskId(task_id) }
    return json(response)
  })

  router.get('/sup', async (request: Request, env: Env) => {
    const id = new URL(request.url).searchParams.get('id')
    if (!id) {
      return json({ error: 'Missing id' }, 400)
    }
    const name = decodeProviderName(id)
    if (!isProviderName(name)) {
      return json({ error: 'Unknown provider' }, 400)
    }
    const provider = createProvider(name)
    const config = provider.resolveConfig(env)
    if (!config) {
      return json({ error: `${name} worker not configured` }, 503)
    }
    const { originalTaskId } = provider.decodeTaskId(id)
    const result = await provider.fetchTaskStatus(originalTaskId, config)
    const response: Schema['SupResponse'] = { status: result.status }
    if (result.status === 'COMPLETED') {
      const output = api.shape.output.safeParse(result.output)
      if (!output.success) {
        return json({ error: 'Invalid worker output' }, 502)
      }
      response.output = output.data
    }
    return json(response)
  })

  router.all('*', async () => json({ error: 'Not Found' }, 404))

  return router
}
