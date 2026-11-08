import { z } from "zod"

export const envSchema = z.object({
  OPENAI_API_KEY: z.string().min(1).optional(),
  ELEVENLABS_API_KEY: z.string().min(1).optional(),
  ELEVENLABS_AGENT_ID: z.string().min(1).optional(),
  SECRET_WORKER_URL: z.url().optional(),
  VOICE_WORKER_AUTH_TOKEN: z.string().min(1).optional(),
})
