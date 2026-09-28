import { Router } from 'itty-router'
import { type Env } from './index'
import createProvider from './providers/create-provider'

const ROUTER_STATUS: Record<string, string> = {
  pending: 'BUSY',
  processing: 'BUSY',
  completed: 'DONE',
  failed: 'REJECTED',
  cancelled: 'REJECTED'
}

export const router = Router()

router.use('*', async ({ request, env }: { request: Request; env: Env }, next: () => Promise<Response>) => {
  const authHeader = request.headers.get('Authorization')
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' }
    })
  }
  const token = authHeader.substring(7)
  if (token !== env.AUTH_TOKEN) {
    return new Response(JSON.stringify({ error: 'Invalid token' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' }
    })
  }
  await next()
})

router.post('/queue', async ({ request, env }: { request: Request; env: Env }) => {
  const body = await request.json() as { input: Record<string, unknown> }
  const { input } = body
  const provider = createProvider({
    provider: env.PROVIDER_TYPE,
    appName: env.PROVIDER_APP_NAME,
    endpointName: env.PROVIDER_ENDPOINT_NAME
  })
  const { task_id } = await provider.pushToTaskQueue(input, env)
  return new Response(JSON.stringify({ task_id }), {
    headers: { 'Content-Type': 'application/json' }
  })
})

router.get('/task/:id', async ({ request, env, params }: { request: Request; env: Env; params: { id: string } }) => {
  const { id: taskId } = params
  const provider = createProvider({
    provider: env.PROVIDER_TYPE,
    appName: env.PROVIDER_APP_NAME,
    endpointName: env.PROVIDER_ENDPOINT_NAME
  })
  const result = await provider.fetchTaskStatus(taskId, env)
  const status = ROUTER_STATUS[result.status] || 'BUSY'
  const response: { status: string; output?: unknown } = { status }
  if (result.status === 'completed') {
    response.output = result.output
  }
  return new Response(JSON.stringify(response), {
    headers: { 'Content-Type': 'application/json' }
  })
})
