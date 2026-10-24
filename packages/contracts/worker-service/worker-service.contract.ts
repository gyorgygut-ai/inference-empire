import { z } from 'zod';
import type { WorkerServiceSchema } from './worker-service.schema';

export const WorkerServiceContract = {
  WORKER_RESOLVED_BEAM_URL: 'WORKER_RESOLVED_BEAM_URL',
  WORKER_RESOLVED_MODAL_URL: 'WORKER_RESOLVED_MODAL_URL',
  WORKER_RESOLVED_FLASH_URL: 'WORKER_RESOLVED_FLASH_URL',
  envFilePath: (taskName: string) => `{workspaceRoot}/dist/${taskName}/contract.env`,
} as const;

export const workerServiceSchema = z.object({
  WORKER_RESOLVED_BEAM_URL: z.string(),
  WORKER_RESOLVED_MODAL_URL: z.string(),
  WORKER_RESOLVED_FLASH_URL: z.string(),
});

export type WorkerServiceContractType = z.infer<typeof workerServiceSchema>;
