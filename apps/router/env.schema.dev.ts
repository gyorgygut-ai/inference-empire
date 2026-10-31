import { z } from 'zod'

export const runtimeEnvSchema = z.object({
  AUTH_TOKEN: z.string().min(32),
  WORKER_BEAM_URL: z.url(),
  SECRET_BEAM_TOKEN: z.string().min(1),
})
export const envSchema = runtimeEnvSchema.extend({ PORT: z.coerce.number().int().min(1024).max(65535) })
