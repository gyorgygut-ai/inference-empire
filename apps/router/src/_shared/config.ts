import { z } from 'zod'

const runtimeConfig = z.object({
  routerToken: z.string().min(32),
  beamUrl: z.url().optional(),
  beamToken: z.string().min(1).optional(),
  cloudflareUrl: z.url().optional(),
})

export interface ServiceBinding {
  fetch(request: Request): Promise<Response>
}

export type RuntimeConfig = z.infer<typeof runtimeConfig> & { cloudflareWorker?: ServiceBinding }

export interface RouterEnv {
  AUTH_TOKEN?: unknown
  WORKER_BEAM_URL?: unknown
  SECRET_BEAM_TOKEN?: unknown
  WORKER_CLOUDFLARE_URL?: unknown
  WORKER_CLOUDFLARE?: ServiceBinding
}

export function readConfig(env: RouterEnv): RuntimeConfig {
  return {
    ...runtimeConfig.parse({
      routerToken: env.AUTH_TOKEN,
      beamUrl: env.WORKER_BEAM_URL,
      beamToken: env.SECRET_BEAM_TOKEN,
      cloudflareUrl: env.WORKER_CLOUDFLARE_URL,
    }),
    cloudflareWorker: env.WORKER_CLOUDFLARE,
  }
}
