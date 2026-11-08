import "server-only"
import { envSchema } from "./config.schema"

const env = envSchema.parse(process.env)

export const config = {
  openAiApiKey: env.OPENAI_API_KEY,
  elevenLabsApiKey: env.ELEVENLABS_API_KEY,
  elevenLabsAgentId: env.ELEVENLABS_AGENT_ID,
  voiceWorkerUrl: env.SECRET_WORKER_URL,
  voiceWorkerAuthToken: env.VOICE_WORKER_AUTH_TOKEN,
}
