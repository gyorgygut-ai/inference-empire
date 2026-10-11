import { z } from 'zod';

export const envSchema = z.object({
  APP_URL: z.string().url(),
  BEAM_URL: z.string().url(),
  BEAM_TASK_API: z.string().url().optional(),
  FLASH_URL: z.string().url().optional(),
  FLASH_ENDPOINT: z.string().optional(),
  ROUTER_FAMILY: z.string().optional(),
  SECRET_AUTH_TOKEN: z.string().min(32),
});

export type RouterEnv = z.infer<typeof envSchema>;
