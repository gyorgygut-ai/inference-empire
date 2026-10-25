import { z } from 'zod';
import { WORKER_RESOLVED_BEAM_URL, WORKER_RESOLVED_MODAL_URL } from './keys';

export const WorkerServiceContractFlux2Dev = {
  keys: [WORKER_RESOLVED_MODAL_URL, WORKER_RESOLVED_BEAM_URL] as const,
  envFilePath: 'dist/flux2/dev.env',
};

export const workerServiceFlux2DevSchema = z.object({
  WORKER_RESOLVED_MODAL_URL: z.string().url(),
  WORKER_RESOLVED_BEAM_URL: z.string().url(),
});
