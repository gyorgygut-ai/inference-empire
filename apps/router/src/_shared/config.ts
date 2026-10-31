import { z } from 'zod'

const runtimeConfig = z.object({
  routerToken: z.string().min(32),
  beamUrl: z.url(),
  beamToken: z.string().min(1),
})

export type RuntimeConfig = z.infer<typeof runtimeConfig>

export type RouterEnv = Record<string, unknown>

export function readConfig(env: RouterEnv): RuntimeConfig {
  return runtimeConfig.parse({
    routerToken: env.AUTH_TOKEN,
    beamUrl: env.WORKER_BEAM_URL,
    beamToken: env.SECRET_BEAM_TOKEN,
  })
}
