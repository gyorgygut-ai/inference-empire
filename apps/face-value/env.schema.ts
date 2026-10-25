import "server-only";
import type { z } from "zod";
import { taskQueueServiceFlux2DevSchema } from "@inference/contracts";

export const envSchema = taskQueueServiceFlux2DevSchema.pick({
  ROUTER_RESOLVED_URL: true,
  ROUTER_GENERATED_AUTH_TOKEN: true,
});

export type Env = z.infer<typeof envSchema>;
