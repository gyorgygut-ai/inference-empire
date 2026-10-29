import { Router } from 'itty-router'
import { z } from 'zod'
import type { RouterEnv, RuntimeConfig } from './config'
import { pickStrategy } from './services/pick-strategy'
import { createStrategy } from './services/create-strategy'
import { StrategyUnavailableError, taskStatusSchema } from './strategies/strategy'
import { decodeTaskId, encodeTaskId } from './task-id'

function json(body: unknown, status = 200) {
  return Response.json(body, { status })
}

interface Dependencies {
  readConfig: (env: RouterEnv) => RuntimeConfig;
  fetchImpl?: typeof fetch;
}

export function createRouter<Api extends z.ZodObject<{ input: z.ZodType; output: z.ZodType }>>(
  api: Api, base: string, dependencies: Dependencies,
) {
  const router = Router({ base })
  function authenticate(request: Request, env: RouterEnv) {
    let config: RuntimeConfig
    try { config = dependencies.readConfig(env) }
    catch { return json({ error: 'Router not configured' }, 503) }
    if (request.headers.get('Authorization') !== `Bearer ${config.routerToken}`) {
      return json({ error: 'Unauthorized' }, 401)
    }
    return config
  }
  function upstreamError(error: unknown) {
    return json({ error: error instanceof StrategyUnavailableError ? 'Strategy unavailable' : 'Worker request failed' },
      error instanceof StrategyUnavailableError ? 503 : 502)
  }

  router.get('/', () => json({ status: 'ok' }))

  router.post('/q', async (request: Request, env: RouterEnv) => {
    const config = authenticate(request, env)
    if (config instanceof Response) {return config}
    let body: unknown
    try { body = await request.json() }
    catch { return json({ error: 'Invalid JSON' }, 400) }
    const envelope = z.object({ input: api.shape.input }).safeParse(body)
    if (!envelope.success) {return json({ error: 'Invalid input' }, 400)}
    try {
      const provider = pickStrategy()
      const strategy = createStrategy(provider, config, dependencies.fetchImpl)
      const result = await strategy.pushToTaskQueue(envelope.data.input)
      return json({ task_id: encodeTaskId(provider, result.task_id) })
    } catch (error) { return upstreamError(error) }
  })

  router.get('/sup', async (request: Request, env: RouterEnv) => {
    const config = authenticate(request, env)
    if (config instanceof Response) {return config}
    const id = new URL(request.url).searchParams.get('id')
    if (!id) {return json({ error: 'Missing task id' }, 400)}
    let decoded: ReturnType<typeof decodeTaskId>
    try { decoded = decodeTaskId(id) }
    catch { return json({ error: 'Invalid task id' }, 400) }
    try {
      const strategy = createStrategy(decoded.provider, config, dependencies.fetchImpl)
      const result = await strategy.fetchTaskStatus(decoded.originalTaskId)
      const status = taskStatusSchema.parse(result.status)
      if (status !== 'COMPLETED') {return json({ status })}
      const output = api.shape.output.safeParse(result.output)
      if (!output.success) {return json({ error: 'Invalid worker output' }, 502)}
      return json({ status, output: output.data })
    } catch (error) { return upstreamError(error) }
  })
  router.all('*', () => json({ error: 'Not Found' }, 404))
  return router
}
