import { z } from "zod";

export const routerPortsSchema = z.object({
  FLUX2_ROUTER_PORT: z.coerce.number().int().min(1).max(65535),
  KREA2_ROUTER_PORT: z.coerce.number().int().min(1).max(65535),
});

export const envSchema = z.object({
  BEAM_WORKER_URL: z.string().url().optional(),
  FLASH_WORKER_URL: z.string().url().optional(),
  MODAL_WORKER_URL: z.string().url().optional(),
  SECRET_AUTH_TOKEN: z.string().min(32),
  PORT: z.coerce.number().int().min(1).max(65535),
  ROUTER_MODEL: z.enum(["flux2", "krea2"]),
});

export type RouterPorts = z.infer<typeof routerPortsSchema>;
export type RouterEnv = z.infer<typeof envSchema>;
