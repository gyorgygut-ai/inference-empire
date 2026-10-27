import { z } from 'zod'
import { envSchema as runtimeEnvSchema } from './env.schema.deploy'

export const envSchema = runtimeEnvSchema.extend({ PORT: z.coerce.number().int().min(1024).max(65535) })
