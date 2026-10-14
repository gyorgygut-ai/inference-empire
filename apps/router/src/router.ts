import { Router } from 'itty-router'
import { type Env } from './index'
import createProvider, { isProviderName, type ProviderConfigs, type ProviderName } from './providers/create-provider'
import { pickTaskHandler } from './pick-task-handler'
import { decodeTaskId, encodeTaskId } from './task-id'
import type { AddToQueueRequest as Flux2Request, AddToQueueResponse, SupResponse } from '../generated/api-flux2'
import type { AddToQueueRequest as Krea2Request } from '../generated/api-krea2'

export const router = Router()

router.all('*', async (request: Request, env: Env) => {
  const authHeader = request.headers.get('Authorization')
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' }
    })
  }
  if (authHeader.substring(7) !== env.SECRET_AUTH_TOKEN) {
    return new Response(JSON.stringify({ error: 'Invalid token' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' }
    })
  }
})

router.post('/q', async (request: Request, env: Env) => {
  const body = await request.json() as Flux2Request | Krea2Request
  const name = pickTaskHandler()
  const provider = createProvider(name)
  const { task_id } = await provider.pushToTaskQueue(body.input, resolveConfig(name, env))
  const response: AddToQueueResponse = { task_id: encodeTaskId(name, task_id) }
  return new Response(JSON.stringify(response), {
    headers: { 'Content-Type': 'application/json' }
  })
})

router.get('/sup', async (request: Request, env: Env) => {
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
  const response: SupResponse = { status: result.status as SupResponse['status'] }
  if (result.status === 'COMPLETED') {
    response.output = result.output as SupResponse['output']
  }
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
  if (name === 'beam') {
    return {
      url: env.BEAM_WORKER_URL ?? '',
      taskApi: 'https://api.beam.cloud'
    } as ProviderConfigs[K]
  }
  if (name === 'flash') {
    return {
      url: env.FLASH_WORKER_URL ?? '',
      endpointName: ''
    } as ProviderConfigs[K]
  }
  return {
    url: env.MODAL_WORKER_URL ?? ''
  } as ProviderConfigs[K]
}
