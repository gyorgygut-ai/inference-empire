import { z } from "zod";
import { envSchema } from "./env.schema";

export const flux2Schema = envSchema.extend({
  FLUX2_ROUTER_VERCEL_TOKEN: z.string().min(1),
  FLUX2_ROUTER_VERCEL_ORG_ID: z.string().min(1),
  FLUX2_ROUTER_VERCEL_PROJECT_ID: z.string().min(1),
});
