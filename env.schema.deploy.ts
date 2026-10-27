import { z } from 'zod'
import { envSchema as workerEnvSchema, providerCredentialsSchema } from './env.schema'

export const envSchema = workerEnvSchema.extend(providerCredentialsSchema.shape).extend({
  CLOUDFLARE_ACCOUNT_ID: z.string().min(1),
  CLOUDFLARE_API_TOKEN: z.string().min(1),
  FACE_VALUE_VERCEL_TOKEN: z.string().min(1),
  FACE_VALUE_VERCEL_ORG_ID: z.string().min(1),
  FACE_VALUE_VERCEL_PROJECT_ID: z.string().min(1),
  ROUTER_FLUX2_GENERATED_AUTH_TOKEN: z.string().min(32),
  ROUTER_TINYSD_GENERATED_AUTH_TOKEN: z.string().min(32),
}).refine(env => env.ROUTER_FLUX2_GENERATED_AUTH_TOKEN !== env.ROUTER_TINYSD_GENERATED_AUTH_TOKEN, {
  message: 'Model families must use distinct router tokens',
})
