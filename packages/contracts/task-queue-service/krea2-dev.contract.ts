import { z } from 'zod'
import { ROUTER_GENERATED_AUTH_TOKEN } from './keys.ts'

export const TaskQueueServiceKrea2DevContract = {
  keys: [ROUTER_GENERATED_AUTH_TOKEN] as const,
  envFilePath: 'dist/krea2/dev.env',
}

export const TaskQueueServiceKrea2DevResolvers = {
  ROUTER_GENERATED_AUTH_TOKEN: 'tools/orchestrator/src/resolve-auth-token.ts dist/krea2/dev.env ROUTER_GENERATED_AUTH_TOKEN',
}

export const taskQueueServiceKrea2DevSchema = z.object({
  ROUTER_GENERATED_AUTH_TOKEN: z.string().min(32),
})
