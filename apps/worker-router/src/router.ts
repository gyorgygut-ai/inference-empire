import { Router } from 'itty-router'
import { type Env } from './providers/create-provider'

export const router = Router({ base: '/inquire' })

router.use('*', async ({ request }: { request: Request }, next: () => Promise<Response>) => {
  const authHeader = request.headers.get('Authorization')
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return new Response(JSON.stringify({ error: 'Unauthorized' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' }
    })
  }
  const token = authHeader.substring(7)
  if (token !== 'router-2026-09-26-23su5t') {
    return new Response(JSON.stringify({ error: 'Invalid token' }), {
      status: 401,
      headers: { 'Content-Type': 'application/json' }
    })
  }
  await next()
})

router.post('/infer', async ({ request, env }: { request: Request; env: Env }) => {
  const body: { prompt: string } = await request.json()
  const { prompt } = body
  const { default: selectProvider } = await import('./providers/select-provider')
  const provider = selectProvider({ provider: 'modal' })
  const { task_id } = await provider.pushToTaskQueue(prompt, env)
  return new Response(JSON.stringify({ task_id }), {
    headers: { 'Content-Type': 'application/json' }
  })
})

router.get('/inquire', async ({ request, env }: { request: Request; env: Env }) => {
  const url = new URL(request.url)
  const taskId = url.searchParams.get('taskId')
  if (!taskId) {
    return new Response(JSON.stringify({ error: 'Missing taskId' }), {
      status: 400,
      headers: { 'Content-Type': 'application/json' }
    })
  }
  const { default: selectProvider } = await import('./providers/select-provider')
  const decoded = selectProvider({}).decodeTaskId(taskId)
  const provider = selectProvider({ provider: decoded.provider })
  const result = await provider.fetchTaskStatus(decoded.originalTaskId, env)
  return new Response(JSON.stringify(result), {
    headers: { 'Content-Type': 'application/json' }
  })
})
