import { z } from 'zod';

export const envSchema = z.object({
  APP_URL: z.string().url(),
  SECRET_AUTH_TOKEN: z.string().min(32),
});

export type RouterEnv = z.infer<typeof envSchema>;
