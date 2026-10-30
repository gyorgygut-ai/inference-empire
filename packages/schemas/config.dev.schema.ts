import { z } from 'zod'

export const configSchema = z.object({
  R2_BUCKET: z.string().min(1),
  ROUTER_FLUX2_PORT: z.coerce.number().int().min(1024).max(65535),
  ROUTER_TINYSD_PORT: z.coerce.number().int().min(1024).max(65535),
  FACE_VALUE_PORT: z.coerce.number().int().min(1024).max(65535),
  VOICE_CHAT_PORT: z.coerce.number().int().min(1024).max(65535),
  ROUTER_FLUX2_GENERATED_AUTH_TOKEN: z.string().min(32),
  ROUTER_TINYSD_GENERATED_AUTH_TOKEN: z.string().min(32),
}).refine(
  config => new Set([
    config.ROUTER_FLUX2_PORT,
    config.ROUTER_TINYSD_PORT,
    config.FACE_VALUE_PORT,
    config.VOICE_CHAT_PORT,
  ]).size === 4,
  { message: 'Development ports must be distinct' },
).refine(
  config => config.ROUTER_FLUX2_GENERATED_AUTH_TOKEN !== config.ROUTER_TINYSD_GENERATED_AUTH_TOKEN,
  { message: 'Model families must use distinct router tokens' },
)

export const envSchema = configSchema
