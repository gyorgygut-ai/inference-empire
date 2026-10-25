import { z } from 'zod';
import {
  WORKER_RESOLVED_BEAM_URL,
  WORKER_RESOLVED_FLASH_URL,
  WORKER_RESOLVED_MODAL_URL,
} from './keys.ts';

export const WorkerServiceContractrealtime_voiceDeploy = {
  keys: [WORKER_RESOLVED_MODAL_URL, WORKER_RESOLVED_BEAM_URL, WORKER_RESOLVED_FLASH_URL] as const,
  envFilePath: 'dist/workers-realtime_voice/deploy.env',
};

export const workerServicerealtime_voiceDeploySchema = z.object({
  WORKER_RESOLVED_MODAL_URL: z.string().url().optional(),
  WORKER_RESOLVED_BEAM_URL: z.string().url(),
  WORKER_RESOLVED_FLASH_URL: z.string().url(),
});
