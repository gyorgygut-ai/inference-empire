import "server-only"
import { realtimeToken } from "@tanstack/ai"
import { openaiRealtimeToken } from "@tanstack/ai-openai"
import { config } from "@/config"

export async function POST(request: Request) {
  if (!config.openAiApiKey) {
    return Response.json({ error: "OpenAI is not configured" }, { status: 503 })
  }

  try {
    const token = await realtimeToken({
      adapter: openaiRealtimeToken({ model: "gpt-realtime-2.1" }),
      abortSignal: request.signal,
    })
    return Response.json(token, { headers: { "Cache-Control": "no-store" } })
  } catch {
    return Response.json({ error: "Unable to create an OpenAI voice session" }, { status: 502 })
  }
}
