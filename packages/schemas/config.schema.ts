import { z } from 'zod'
import { api as runtimeConfigSchema } from './env/config.schema'

const parsedConfigSchema = runtimeConfigSchema.extend({
  DEV_ROUTER_FLUX2_PORT: z.coerce.number().pipe(runtimeConfigSchema.shape.DEV_ROUTER_FLUX2_PORT),
  DEV_ROUTER_TINYSD_PORT: z.coerce.number().pipe(runtimeConfigSchema.shape.DEV_ROUTER_TINYSD_PORT),
  DEV_FACE_VALUE_PORT: z.coerce.number().pipe(runtimeConfigSchema.shape.DEV_FACE_VALUE_PORT),
  DEV_VOICE_CHAT_PORT: z.coerce.number().pipe(runtimeConfigSchema.shape.DEV_VOICE_CHAT_PORT),
})

export const configSchema = parsedConfigSchema.refine(
  config => new Set([
    config.DEV_ROUTER_FLUX2_PORT,
    config.DEV_ROUTER_TINYSD_PORT,
    config.DEV_FACE_VALUE_PORT,
    config.DEV_VOICE_CHAT_PORT,
  ]).size === 4,
  { message: 'Development ports must be distinct' },
).refine(
  config => config.GENERATED_ROUTER_FLUX2_AUTH_TOKEN !== config.GENERATED_ROUTER_TINYSD_AUTH_TOKEN,
  { message: 'Model families must use distinct router tokens' },
).refine(
  config => new Set([
    config.GENERATED_STT_AUDIO_TRANSCRIPTIONS_API_KEY,
    config.GENERATED_LLM_CHAT_COMPLETIONS_API_KEY,
    config.GENERATED_TTS_AUDIO_SPEECH_API_KEY,
    config.GENERATED_VOICE_WORKER_AUTH_TOKEN,
  ]).size === 4,
  { message: 'Voice service credentials must be distinct' },
)

export const envSchema = configSchema
