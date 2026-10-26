import { z } from 'zod'
import { ROUTER_GENERATED_AUTH_TOKEN, ROUTER_RESOLVED_URL } from './keys.ts'

export const TaskQueueServiceFlux2DeployContract = {
  keys: [ROUTER_RESOLVED_URL, ROUTER_GENERATED_AUTH_TOKEN] as const,
  envFilePath: 'dist/functions/flux2-deploy.env',
}

export const TaskQueueServiceFlux2DeployResolvers = {
  ROUTER_RESOLVED_URL: 'tools/orchestrator/src/get-netlify-url.ts "{options.siteId}"',
  ROUTER_GENERATED_AUTH_TOKEN: 'tools/orchestrator/src/resolve-auth-token.ts dist/functions/flux2-deploy.env ROUTER_GENERATED_AUTH_TOKEN',
}

export const taskQueueServiceFlux2DeploySchema = z.object({
  ROUTER_RESOLVED_URL: z.string().url(),
  ROUTER_GENERATED_AUTH_TOKEN: z.string().min(32),
})
