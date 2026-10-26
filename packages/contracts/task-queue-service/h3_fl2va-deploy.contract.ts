import { z } from 'zod'
import { ROUTER_GENERATED_AUTH_TOKEN, ROUTER_RESOLVED_URL } from './keys.ts'

export const TaskQueueServiceContracth3_fl2vaDeploy = {
  keys: [ROUTER_RESOLVED_URL, ROUTER_GENERATED_AUTH_TOKEN] as const,
  envFilePath: 'dist/functions/h3_fl2va-deploy.env',
}

export const taskQueueServiceh3_fl2vaDeploySchema = z.object({
  ROUTER_RESOLVED_URL: z.string().url(),
  ROUTER_GENERATED_AUTH_TOKEN: z.string().min(32),
})
