import { z } from 'zod'

const runtimeConfig = z.object({
  routerToken: z.string().min(32),
  beamUrl: z.url(),
  beamToken: z.string().min(1),
})

export type RuntimeConfig = z.infer<typeof runtimeConfig>

export function readConfig(env: NodeJS.ProcessEnv = process.env): RuntimeConfig {
  return runtimeConfig.parse({
    routerToken: env.ROUTER_GENERATED_AUTH_TOKEN,
    beamUrl: env.WORKER_RESOLVED_BEAM_URL,
    beamToken: env.BEAM_TOKEN,
  })
}