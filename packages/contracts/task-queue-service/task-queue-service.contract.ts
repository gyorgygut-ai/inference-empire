import { z } from 'zod';
import type { TaskQueueServiceSchema } from './task-queue-service.schema';

export const TaskQueueServiceContract = {
  ROUTER_RESOLVED_URL: 'ROUTER_RESOLVED_URL',
  ROUTER_GENERATED_AUTH_TOKEN: 'ROUTER_GENERATED_AUTH_TOKEN',
  envFilePath: '{workspaceRoot}/dist/{taskName}/',
} as const;

export const taskQueueServiceSchema = z.object({
  ROUTER_RESOLVED_URL: z.string(),
  ROUTER_GENERATED_AUTH_TOKEN: z.string(),
  envFilePath: z.string(),
});

export type TaskQueueServiceContractType = z.infer<typeof taskQueueServiceSchema>;
