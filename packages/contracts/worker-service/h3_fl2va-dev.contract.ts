import { z } from 'zod';
import { WORKER_RESOLVED_BEAM_URL, WORKER_RESOLVED_MODAL_URL } from './keys.ts';

export const WorkerServiceContracth3_fl2vaDev = {
  keys: [WORKER_RESOLVED_MODAL_URL, WORKER_RESOLVED_BEAM_URL] as const,
  envFilePath: 'dist/workers-h3_fl2va/dev.env',
};

export const workerServiceh3_fl2vaDevSchema = z.object({
  WORKER_RESOLVED_MODAL_URL: z.string().url().optional(),
  WORKER_RESOLVED_BEAM_URL: z.string().url(),
});
