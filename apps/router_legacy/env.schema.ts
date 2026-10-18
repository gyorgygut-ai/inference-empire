import { z } from "zod";

export const envSchema = z.object({
  MODAL_WORKER_URL: z.url().optional(),
  BEAM_WORKER_URL: z.url().optional(),
  ROUTER_AUTH_TOKEN: z.string().min(32),
  PORT: z.coerce.number().int().min(1).max(65535),
  FLASH_WORKER_URL: z.url().optional(),
});

export type Env = z.infer<typeof envSchema>;
