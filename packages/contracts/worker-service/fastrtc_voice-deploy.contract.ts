import { z } from 'zod'
import { WORKER_RESOLVED_BEAM_URL, WORKER_RESOLVED_MODAL_URL } from './keys.ts'

export const workerServiceFastrtcVoiceDeploySchema = z.object({
  WORKER_RESOLVED_MODAL_URL: z.url().optional(),
  WORKER_RESOLVED_BEAM_URL: z.url().optional(),
})

export const WorkerServiceFastrtcVoiceDeployContract = {
  keys: [WORKER_RESOLVED_MODAL_URL, WORKER_RESOLVED_BEAM_URL] as const,
  envFilePath: 'dist/workers-fastrtc_voice/deploy.env',
  resolvers: {
    WORKER_RESOLVED_MODAL_URL: 'npx tsx tools/orchestrator/src/get-modal-url.ts workers-fastrtc_voice',
    WORKER_RESOLVED_BEAM_URL: 'npx tsx tools/orchestrator/src/get-beam-url.ts workers-fastrtc_voice',
  },
}
