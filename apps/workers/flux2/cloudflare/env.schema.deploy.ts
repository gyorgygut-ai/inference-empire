import { z } from 'zod'

export const envSchema = z.object({ AUTH_TOKEN: z.string().min(32) })
