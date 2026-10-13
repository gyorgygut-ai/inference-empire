import { z } from "zod";

export const envSchema = z.object({
  BEAM_WORKER_URL: z.string().url().optional(),
  FLASH_WORKER_URL: z.string().url().optional(),
  MODAL_WORKER_URL: z.string().url().optional(),
  SECRET_AUTH_TOKEN: z.string().min(32),
});

export type RouterEnv = z.infer<typeof envSchema>;
