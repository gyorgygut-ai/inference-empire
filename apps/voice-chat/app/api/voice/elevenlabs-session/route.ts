import "server-only"
import { realtimeToken } from "@tanstack/ai"
import { elevenlabsRealtimeToken } from "@tanstack/ai-elevenlabs"
import { config } from "@/config"

export async function POST(request: Request) {
  if (!config.elevenLabsApiKey || !config.elevenLabsAgentId) {
    return Response.json({ error: "ElevenLabs is not configured" }, { status: 503 })
  }

  try {
    const token = await realtimeToken({
      adapter: elevenlabsRealtimeToken({ agentId: config.elevenLabsAgentId }),
      abortSignal: request.signal,
    })
    return Response.json(token, {
      headers: { "Cache-Control": "no-store" },
    })
  } catch {
    return Response.json({ error: "Unable to create an ElevenLabs voice session" }, { status: 502 })
  }
}
