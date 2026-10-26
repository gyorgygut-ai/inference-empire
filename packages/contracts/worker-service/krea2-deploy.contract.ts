import { z } from 'zod'
import { WORKER_RESOLVED_BEAM_URL } from './keys.ts'

export const WorkerServiceKrea2DeployContract = {
  keys: [WORKER_RESOLVED_BEAM_URL] as const,
  envFilePath: 'dist/workers-krea2/deploy.env',
}

export const WorkerServiceKrea2DeployResolvers = {
  WORKER_RESOLVED_BEAM_URL: 'tools/orchestrator/src/get-beam-url.ts workers-krea2',
}

export const workerServiceKrea2DeploySchema = z.object({
  WORKER_RESOLVED_BEAM_URL: z.string().url(),
})
