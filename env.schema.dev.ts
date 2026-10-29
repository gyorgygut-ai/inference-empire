import { z } from 'zod'
import { envSchema as workerEnvSchema, providerCredentialsSchema } from './env.schema'

export const envSchema = workerEnvSchema.extend(providerCredentialsSchema.shape).extend({
  ROUTER_FLUX2_PORT: z.coerce.number().int().min(1024).max(65535),
  ROUTER_TINYSD_PORT: z.coerce.number().int().min(1024).max(65535),
  FACE_VALUE_PORT: z.coerce.number().int().min(1024).max(65535),
  VOICE_CHAT_PORT: z.coerce.number().int().min(1024).max(65535),
  ROUTER_FLUX2_GENERATED_AUTH_TOKEN: z.string().min(32),
  ROUTER_TINYSD_GENERATED_AUTH_TOKEN: z.string().min(32),
}).refine(env => new Set([env.ROUTER_FLUX2_PORT, env.ROUTER_TINYSD_PORT, env.FACE_VALUE_PORT, env.VOICE_CHAT_PORT]).size === 4, {
  message: 'Development ports must be distinct',
}).refine(env => env.ROUTER_FLUX2_GENERATED_AUTH_TOKEN !== env.ROUTER_TINYSD_GENERATED_AUTH_TOKEN, {
  message: 'Model families must use distinct router tokens',
})
