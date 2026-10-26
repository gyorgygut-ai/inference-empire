import { z } from 'zod'
import { ROUTER_GENERATED_AUTH_TOKEN } from './keys.ts'

export const TaskQueueServiceFlux2DevContract = {
  keys: [ROUTER_GENERATED_AUTH_TOKEN] as const,
  envFilePath: 'dist/functions/flux2-dev.env',
}

export const TaskQueueServiceFlux2DevResolvers = {
  ROUTER_GENERATED_AUTH_TOKEN: 'tools/orchestrator/src/resolve-auth-token.ts dist/functions/flux2-dev.env ROUTER_GENERATED_AUTH_TOKEN',
}

export const taskQueueServiceFlux2DevSchema = z.object({
  ROUTER_GENERATED_AUTH_TOKEN: z.string().min(32),
})
