import { Router } from 'itty-router'
import { type Env } from './index'
import createProvider, { isProviderName, type ProviderConfigs, type ProviderName } from './providers/create-provider'
import { pickTaskHandler } from './pick-task-handler'
import { decodeTaskId, encodeTaskId } from './task-id'
import type { InferRequest, InferResponse, InquireResponse } from '../generated/router_api'

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
  const body = await request.json() as InferRequest
  const name = pickTaskHandler()
  const provider = createProvider(name)
  const { task_id } = await provider.pushToTaskQueue(body.input, resolveConfig(name, env))
  const response: InferResponse = { task_id: encodeTaskId(name, task_id) }
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
  const response: InquireResponse = { status: result.status as InquireResponse['status'] }
  if (result.status === 'COMPLETED') {
    response.output = result.output as InquireResponse['output']
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

function resolveConfig<K extends ProviderName>(name: K, _env: Env): ProviderConfigs[K] {
  if (name === 'beam') {
    return {
      url: '',
      taskApi: 'https://api.beam.cloud'
    } as ProviderConfigs[K]
  }
  return {
    url: '',
    endpointName: ''
  } as ProviderConfigs[K]
}
