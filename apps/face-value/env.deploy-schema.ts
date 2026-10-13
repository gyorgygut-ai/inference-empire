import { z } from "zod"

export const deployEnvSchema = z.object({
  FACE_VALUE_VERCEL_TOKEN: z.string().min(1),
  FACE_VALUE_VERCEL_ORG_ID: z.string().min(1),
  FACE_VALUE_VERCEL_PROJECT_ID: z.string().min(1),
})