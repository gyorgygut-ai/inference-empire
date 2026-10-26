import { z } from 'zod'
import { ROUTER_GENERATED_AUTH_TOKEN, ROUTER_RESOLVED_URL } from './keys.ts'

export const TaskQueueServiceContracth3_ref2vaDev = {
  keys: [ROUTER_RESOLVED_URL, ROUTER_GENERATED_AUTH_TOKEN] as const,
  envFilePath: 'dist/functions/h3_ref2va-dev.env',
}

export const taskQueueServiceh3_ref2vaDevSchema = z.object({
  ROUTER_RESOLVED_URL: z.string().url(),
  ROUTER_GENERATED_AUTH_TOKEN: z.string().min(32),
})
