import { Router } from 'itty-router'
import { type Env } from './index.js'
import createProvider, { isProviderName, type ProviderConfigs, type ProviderName } from './providers/create-provider.js'
import { pickTaskHandler } from './pick-task-handler.js'
import { decodeTaskId, encodeTaskId } from './task-id.js'

export function createRouter<
  TAddRequest extends { input: Record<string, unknown> },
  TAddResponse extends { task_id: string },
  TSupResponse extends { status: string; output?: unknown },
>() {
  const router = Router()

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
    const body = await request.json() as TAddRequest
    const name = pickTaskHandler()
    const provider = createProvider(name)
    const { task_id } = await provider.pushToTaskQueue(body.input, resolveConfig(name, env))
    const response = { task_id: encodeTaskId(name, task_id) } as TAddResponse
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
    const response = { status: result.status } as TSupResponse
    if (result.status === 'COMPLETED') {
      response.output = result.output
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

  return router
}

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
