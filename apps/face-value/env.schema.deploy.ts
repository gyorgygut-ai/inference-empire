import { z } from 'zod'

export const envSchema = z.object({ ROUTER_URL: z.url(), ROUTER_AUTH_TOKEN: z.string().min(32) })
