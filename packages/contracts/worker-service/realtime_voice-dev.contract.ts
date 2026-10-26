import { z } from 'zod'
import { WORKER_RESOLVED_BEAM_URL, WORKER_RESOLVED_MODAL_URL } from './keys.ts'

export const WorkerServiceContractrealtime_voiceDev = {
  keys: [WORKER_RESOLVED_MODAL_URL, WORKER_RESOLVED_BEAM_URL] as const,
  envFilePath: 'dist/workers-realtime_voice/dev.env',
}

export const workerServicerealtime_voiceDevSchema = z.object({
  WORKER_RESOLVED_MODAL_URL: z.string().url().optional(),
  WORKER_RESOLVED_BEAM_URL: z.string().url(),
})
