import { loadModel } from '../src/models/index.js'
import type { Env } from '../src/index.js'

function resolveEnv(): Env {
  return {
    SECRET_AUTH_TOKEN: process.env.SECRET_AUTH_TOKEN ?? '',
    MODAL_WORKER_URL: process.env.MODAL_WORKER_URL,
    BEAM_WORKER_URL: process.env.BEAM_WORKER_URL,
    FLASH_WORKER_URL: process.env.FLASH_WORKER_URL,
  }
}

let loaded: Awaited<ReturnType<typeof loadModel>> | undefined

export default async function handler(request: Request): Promise<Response> {
  loaded ??= await loadModel()
  return loaded.router.fetch(request, resolveEnv(), undefined)
}
