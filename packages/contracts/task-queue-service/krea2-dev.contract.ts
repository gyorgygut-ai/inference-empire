import { z } from 'zod';
import { ROUTER_GENERATED_AUTH_TOKEN, ROUTER_RESOLVED_URL } from './keys';

export const TaskQueueServiceContractKrea2Dev = {
  keys: [ROUTER_RESOLVED_URL, ROUTER_GENERATED_AUTH_TOKEN] as const,
  envFilePath: 'dist/krea2/dev.env',
};

export const taskQueueServiceKrea2DevSchema = z.object({
  ROUTER_RESOLVED_URL: z.string().url(),
  ROUTER_GENERATED_AUTH_TOKEN: z.string().min(32),
});
