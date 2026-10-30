import { z } from 'zod'

export const configSchema = z.object({
  R2_BUCKET: z.string().min(1),
  ROUTER_FLUX2_GENERATED_AUTH_TOKEN: z.string().min(32),
  ROUTER_TINYSD_GENERATED_AUTH_TOKEN: z.string().min(32),
}).refine(
  config => config.ROUTER_FLUX2_GENERATED_AUTH_TOKEN !== config.ROUTER_TINYSD_GENERATED_AUTH_TOKEN,
  { message: 'Model families must use distinct router tokens' },
)

export const envSchema = configSchema
