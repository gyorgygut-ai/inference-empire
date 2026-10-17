import { z } from "zod";

export const envSchema = z.object({
  MODAL_WORKER_URL: z.url().optional(),
  BEAM_WORKER_URL: z.url().optional(),
  ROUTER_URL: z.url(),
  ROUTER_AUTH_TOKEN: z.string().min(32),
});

export type Env = z.infer<typeof envSchema>;
