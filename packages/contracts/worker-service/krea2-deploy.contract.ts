import { z } from 'zod';
import { WORKER_RESOLVED_MODAL_URL } from './keys.ts';

export const WorkerServiceContractKrea2Deploy = {
  keys: [WORKER_RESOLVED_MODAL_URL] as const,
  envFilePath: 'dist/krea2/deploy.env',
};

export const workerServiceKrea2DeploySchema = z.object({
  WORKER_RESOLVED_MODAL_URL: z.string().url(),
});
