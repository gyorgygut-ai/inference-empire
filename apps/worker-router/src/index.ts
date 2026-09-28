import { router } from './router'

export default {
  async fetch(request: Request, env: Record<string, unknown>, ctx: ExecutionContext) {
    return router.handle(request, env, ctx)
  }
}