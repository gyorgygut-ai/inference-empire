import { Router } from 'itty-router'
import { type Env } from './index'
import createProvider, { isProviderName, type ProviderConfigs, type ProviderName } from './providers/create-provider'
import { pickTaskHandler } from './pick-task-handler'
import { decodeTaskId, encodeTaskId } from './task-id'

export const router = Router()

router.all('*', async (request: Request, env: Env) => {
  const authHeader = request.headers.get('Authorization')
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' }
    })
  }
  if (authHeader.substring(7) !== env.AUTH_TOKEN) {
    return new Response(JSON.stringify({ error: 'Invalid token' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' }
    })
  }
})

router.post('/infer', async (request: Request, env: Env) => {
  const body = await request.json() as { input: Record<string, unknown> }
  const name = pickTaskHandler()
  const provider = createProvider(name)
  const { task_id } = await provider.pushToTaskQueue(body.input, resolveConfig(name, env))
  return new Response(JSON.stringify({ task_id: encodeTaskId(name, task_id) }), {
    headers: { 'Content-Type': 'application/json' }
  })
})

router.get('/inquire', async (request: Request, env: Env) => {
  const id = new URL(request.url).searchParams.get('id')
  if (!id) {
    return new Response(JSON.stringify({ error: 'Missing id' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' }
    })
  }
  const { provider: name, originalTaskId } = decodeTaskId(id)
  if (!isProviderName(name)) {
    return new Response(JSON.stringify({ error: 'Unknown provider' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' }
    })
  }
  const provider = createProvider(name)
  const result = await provider.fetchTaskStatus(originalTaskId, resolveConfig(name, env))
  const response: { status: string; output?: unknown } = { status: result.status }
  if (result.status === 'completed') {
    response.output = result.output
  }
  console.log('request', request)
  console.log('response', response)
  return new Response(JSON.stringify(response), {
    headers: { 'Content-Type': 'application/json' }
  })
})

router.all('*', async () => (
  new Response(JSON.stringify({ error: 'Not Found' }), {
    status: 404,
    headers: { 'Content-Type': 'application/json' }
  })
))

function resolveConfig<K extends ProviderName>(name: K, env: Env): ProviderConfigs[K] {
  const providers = JSON.parse(env.PROVIDERS) as ProviderConfigs
  return providers[name]
}
