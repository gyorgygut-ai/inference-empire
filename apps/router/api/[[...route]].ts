import { router } from '../src/router'
import type { Env } from '../src/index'

function resolveEnv(): Env {
  return {
    SECRET_AUTH_TOKEN: process.env.SECRET_AUTH_TOKEN ?? '',
    MODAL_WORKER_URL: process.env.MODAL_WORKER_URL,
    BEAM_WORKER_URL: process.env.BEAM_WORKER_URL,
    FLASH_WORKER_URL: process.env.FLASH_WORKER_URL,
  }
}

export default async function handler(request: Request): Promise<Response> {
  return router.fetch(request, resolveEnv(), undefined)
}
