import { z } from 'zod';

export const envSchema = z.object({
  ROUTER_FLUX2_APP_URL: z.string().url(),
  ROUTER_FLUX2_SECRET_AUTH_TOKEN: z.string().min(32),
});

export type FaceValueEnv = z.infer<typeof envSchema>;
