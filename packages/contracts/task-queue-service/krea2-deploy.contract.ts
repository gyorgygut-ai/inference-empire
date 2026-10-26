import { z } from 'zod'
import { ROUTER_GENERATED_AUTH_TOKEN, ROUTER_RESOLVED_URL } from './keys.ts'

export const TaskQueueServiceKrea2DeployContract = {
  keys: [ROUTER_RESOLVED_URL, ROUTER_GENERATED_AUTH_TOKEN] as const,
  envFilePath: 'dist/krea2/deploy.env',
}

export const TaskQueueServiceKrea2DeployResolvers = {
  ROUTER_RESOLVED_URL: 'tools/orchestrator/src/get-netlify-url.ts "{options.siteId}"',
  ROUTER_GENERATED_AUTH_TOKEN: 'tools/orchestrator/src/resolve-auth-token.ts dist/krea2/deploy.env ROUTER_GENERATED_AUTH_TOKEN',
}

export const taskQueueServiceKrea2DeploySchema = z.object({
  ROUTER_RESOLVED_URL: z.string().url(),
  ROUTER_GENERATED_AUTH_TOKEN: z.string().min(32),
})
