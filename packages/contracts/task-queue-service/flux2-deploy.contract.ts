import { z } from 'zod';
import { ROUTER_GENERATED_AUTH_TOKEN, ROUTER_RESOLVED_URL } from './keys.ts';

export const TaskQueueServiceContractFlux2Deploy = {
  keys: [ROUTER_RESOLVED_URL, ROUTER_GENERATED_AUTH_TOKEN] as const,
  envFilePath: 'dist/flux2/deploy.env',
};

export const taskQueueServiceFlux2DeploySchema = z.object({
  ROUTER_RESOLVED_URL: z.string().url(),
  ROUTER_GENERATED_AUTH_TOKEN: z.string().min(32),
});
