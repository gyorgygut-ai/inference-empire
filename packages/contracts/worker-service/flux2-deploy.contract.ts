import { z } from 'zod';
import {
  WORKER_RESOLVED_BEAM_URL,
  WORKER_RESOLVED_FLASH_URL,
  WORKER_RESOLVED_MODAL_URL,
} from './keys.ts';

export const WorkerServiceContractFlux2Deploy = {
  keys: [WORKER_RESOLVED_MODAL_URL, WORKER_RESOLVED_BEAM_URL, WORKER_RESOLVED_FLASH_URL] as const,
  envFilePath: 'dist/flux2/deploy.env',
};

export const workerServiceFlux2DeploySchema = z.object({
  WORKER_RESOLVED_MODAL_URL: z.string().url(),
  WORKER_RESOLVED_BEAM_URL: z.string().url(),
  WORKER_RESOLVED_FLASH_URL: z.string().url().optional(),
});
