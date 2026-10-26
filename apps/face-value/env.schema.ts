import "server-only";
import { z } from "zod";

export const envSchema = z.object({
  ROUTER_URL: z.url(),
  ROUTER_AUTH_TOKEN: z.string().min(32),
});

export type Env = z.infer<typeof envSchema>;
