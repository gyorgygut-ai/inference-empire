import { router } from './router'

export interface Env {
  AUTH_TOKEN: string
  PROVIDER_TYPE: 'modal' | 'beam' | 'flash'
  PROVIDER_TOKEN: string
  PROVIDER_API_URL: string
  PROVIDER_APP_NAME?: string
  PROVIDER_ENDPOINT_NAME?: string
}

export default {
  async fetch(request: Request, env: Record<string, string>, _ctx: any) {
    const typedEnv: Env = env as unknown as Env
    return router.handle(request, typedEnv, _ctx)
  }
}
