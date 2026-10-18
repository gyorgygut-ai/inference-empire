import { createRouter } from './router.js'
import type { Env } from '../env.schema.js'

const router = createRouter()

export function handle(request: Request, env: Env): Promise<Response> {
  return router.fetch(request, env, undefined)
}
