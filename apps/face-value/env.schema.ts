import { z } from "zod";

export const envSchema = z.object({
  ROUTER_URL: z.url(),
  SECRET_AUTH_TOKEN: z.string().min(32),
  FACE_VALUE_VERCEL_TOKEN: z.string().min(1),
  FACE_VALUE_VERCEL_ORG_ID: z.string().min(1),
  FACE_VALUE_VERCEL_PROJECT_ID: z.string().min(1),
});
