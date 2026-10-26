import { z } from 'zod'
import { ROUTER_GENERATED_AUTH_TOKEN, ROUTER_RESOLVED_URL } from './keys.ts'

export const TaskQueueServiceContracttiny_sdDev = {
  keys: [ROUTER_RESOLVED_URL, ROUTER_GENERATED_AUTH_TOKEN] as const,
  envFilePath: 'dist/functions/tiny_sd-dev.env',
}

export const taskQueueServicetiny_sdDevSchema = z.object({
  ROUTER_RESOLVED_URL: z.string().url(),
  ROUTER_GENERATED_AUTH_TOKEN: z.string().min(32),
})
