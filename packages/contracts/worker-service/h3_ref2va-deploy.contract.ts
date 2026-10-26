import { z } from 'zod'
import {
  WORKER_RESOLVED_BEAM_URL,
  WORKER_RESOLVED_FLASH_URL,
  WORKER_RESOLVED_MODAL_URL,
} from './keys.ts'

export const WorkerServiceContracth3_ref2vaDeploy = {
  keys: [WORKER_RESOLVED_MODAL_URL, WORKER_RESOLVED_BEAM_URL, WORKER_RESOLVED_FLASH_URL] as const,
  envFilePath: 'dist/workers-h3_ref2va/deploy.env',
}

export const workerServiceh3_ref2vaDeploySchema = z.object({
  WORKER_RESOLVED_MODAL_URL: z.string().url().optional(),
  WORKER_RESOLVED_BEAM_URL: z.string().url(),
  WORKER_RESOLVED_FLASH_URL: z.string().url(),
})
