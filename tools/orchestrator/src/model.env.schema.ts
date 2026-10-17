import { z } from 'zod';

export const modelEnvSchema = z.object({
  MODAL_WORKER_URL: z.string().url().optional(),
  BEAM_WORKER_URL: z.string().url().optional(),
  ROUTER_URL: z.string().url(),
  ROUTER_AUTH_TOKEN: z.string(),
});

export type ModelEnv = z.infer<typeof modelEnvSchema>;
