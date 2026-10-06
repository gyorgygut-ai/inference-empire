import { router } from './router'

export interface Env {
  AUTH_TOKEN: string
  PROVIDERS: string
}

export default {
  async fetch(request: Request, env: Record<string, string>, _ctx: any) {
    const typedEnv: Env = env as unknown as Env
    return router.fetch(request, typedEnv, _ctx)
  }
}
