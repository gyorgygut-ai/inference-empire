import { z } from "zod"

export const api = z.object({ "DEV_ROUTER_FLUX2_PORT": z.number().int().gte(1024).lte(65535), "DEV_ROUTER_TINYSD_PORT": z.number().int().gte(1024).lte(65535), "DEV_FACE_VALUE_PORT": z.number().int().gte(1024).lte(65535), "DEV_VOICE_CHAT_PORT": z.number().int().gte(1024).lte(65535), "DEV_VOICE_WORKER_PORT": z.number().int().gte(1024).lte(65535), "ROUTER_FLUX2_AUTH_TOKEN": z.string().min(32), "ROUTER_TINYSD_AUTH_TOKEN": z.string().min(32), "STT_AUDIO_TRANSCRIPTIONS_API_KEY": z.string().min(32), "LLM_CHAT_COMPLETIONS_API_KEY": z.string().min(32), "TTS_AUDIO_SPEECH_API_KEY": z.string().min(32), "VOICE_WORKER_AUTH_TOKEN": z.string().min(32) })
export type Api = z.infer<typeof api>
