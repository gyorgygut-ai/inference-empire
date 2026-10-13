import { z } from "zod";
import { envSchema } from "./env.schema";

export const flux2Schema = envSchema.extend({
  KREA2_ROUTER_VERCEL_TOKEN: z.string().min(1),
  KREA2_ROUTER_VERCEL_ORG_ID: z.string().min(1),
  KREA2_ROUTER_VERCEL_PROJECT_ID: z.string().min(1),
});
