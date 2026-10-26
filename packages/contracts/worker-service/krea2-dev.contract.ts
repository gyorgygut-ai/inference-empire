import { z } from 'zod'
import { WORKER_RESOLVED_MODAL_URL } from './keys.ts'

export const WorkerServiceContractKrea2Dev = {
  keys: [WORKER_RESOLVED_MODAL_URL] as const,
  envFilePath: 'dist/krea2/dev.env',
}

export const workerServiceKrea2DevSchema = z.object({
  WORKER_RESOLVED_MODAL_URL: z.string().url(),
})
