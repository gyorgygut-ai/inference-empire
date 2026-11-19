import { z } from 'zod'

export const envSchema = z.object({
  AUTH_TOKEN: z.string().min(32),
  WORKER_CLOUDFLARE_URL: z.url(),
})
