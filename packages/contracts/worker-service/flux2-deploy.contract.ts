import { z } from 'zod'
import { WORKER_RESOLVED_BEAM_URL } from './keys.ts'

export const WorkerServiceFlux2DeployContract = {
  keys: [WORKER_RESOLVED_BEAM_URL] as const,
  envFilePath: 'dist/workers-flux2/deploy.env',
}

export const WorkerServiceFlux2DeployResolvers = {
  WORKER_RESOLVED_BEAM_URL: 'tools/orchestrator/src/get-beam-url.ts workers-flux2',
}

export const workerServiceFlux2DeploySchema = z.object({
  WORKER_RESOLVED_MODAL_URL: z.string().url().optional(),
  WORKER_RESOLVED_BEAM_URL: z.string().url(),
  WORKER_RESOLVED_FLASH_URL: z.string().url().optional(),
})
