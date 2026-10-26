import { z } from 'zod'
import { WORKER_RESOLVED_BEAM_URL, WORKER_RESOLVED_MODAL_URL } from './keys.ts'

export const WorkerServiceContracth3_comfyDev = {
  keys: [WORKER_RESOLVED_MODAL_URL, WORKER_RESOLVED_BEAM_URL] as const,
  envFilePath: 'dist/workers-h3_comfy/dev.env',
}

export const workerServiceh3_comfyDevSchema = z.object({
  WORKER_RESOLVED_MODAL_URL: z.string().url().optional(),
  WORKER_RESOLVED_BEAM_URL: z.string().url(),
})
