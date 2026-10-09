import { router } from '../src/router'
import type { Env } from '../src/index'

function resolveEnv(): Env {
  return {
    AUTH_TOKEN: process.env.AUTH_TOKEN ?? '',
    ROUTER_FAMILY: process.env.ROUTER_FAMILY ?? '',
    BEAM_URL: process.env.BEAM_URL ?? '',
    BEAM_TASK_API: process.env.BEAM_TASK_API ?? '',
    FLASH_URL: process.env.FLASH_URL ?? '',
    FLASH_ENDPOINT: process.env.FLASH_ENDPOINT ?? ''
  }
}

export default async function handler(request: Request): Promise<Response> {
  return router.fetch(request, resolveEnv(), undefined)
}
