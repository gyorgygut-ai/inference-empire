import { z } from 'zod'
import { api as runtimeConfigSchema } from './env/config.schema'

const parsedConfigSchema = runtimeConfigSchema.extend({
  DEV_ROUTER_FLUX2_PORT: z.coerce.number().pipe(runtimeConfigSchema.shape.DEV_ROUTER_FLUX2_PORT),
  DEV_ROUTER_TINYSD_PORT: z.coerce.number().pipe(runtimeConfigSchema.shape.DEV_ROUTER_TINYSD_PORT),
  DEV_FACE_VALUE_PORT: z.coerce.number().pipe(runtimeConfigSchema.shape.DEV_FACE_VALUE_PORT),
  DEV_VOICE_CHAT_PORT: z.coerce.number().pipe(runtimeConfigSchema.shape.DEV_VOICE_CHAT_PORT),
  DEV_VOICE_WORKER_PORT: z.coerce.number().pipe(runtimeConfigSchema.shape.DEV_VOICE_WORKER_PORT),
})

export const configSchema = parsedConfigSchema.refine(
  config => new Set([
    config.DEV_ROUTER_FLUX2_PORT,
    config.DEV_ROUTER_TINYSD_PORT,
    config.DEV_FACE_VALUE_PORT,
    config.DEV_VOICE_CHAT_PORT,
    config.DEV_VOICE_WORKER_PORT,
  ]).size === 5,
  { message: 'Development ports must be distinct' },
).refine(
  config => config.ROUTER_FLUX2_AUTH_TOKEN !== config.ROUTER_TINYSD_AUTH_TOKEN,
  { message: 'Model families must use distinct router tokens' },
).refine(
  config => new Set([
    config.STT_AUDIO_TRANSCRIPTIONS_API_KEY,
    config.LLM_CHAT_COMPLETIONS_API_KEY,
    config.TTS_AUDIO_SPEECH_API_KEY,
    config.VOICE_WORKER_AUTH_TOKEN,
  ]).size === 4,
  { message: 'Voice service credentials must be distinct' },
)

export const envSchema = configSchema
