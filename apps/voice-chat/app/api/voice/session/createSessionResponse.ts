import type { RealtimeToken } from "@tanstack/ai"
import { api as voiceSchema } from "../../../../dist/voice.schema"

export async function createSessionResponse(workerUrl?: string, secretBeamToken?: string) {
  if (!workerUrl || !secretBeamToken) {
    return Response.json({ error: "Voice worker is not configured" }, { status: 503 })
  }

  try {
    const response = await fetch(`${workerUrl.replace(/\/$/, "")}/v1/realtime/client_secrets`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${secretBeamToken}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({}),
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    })

    if (!response.ok) {
      return Response.json({ error: "Unable to create a voice session" }, { status: 502 })
    }

    const result: unknown = await response.json()
    const parsed = voiceSchema.shape.client_secret_output.unwrap().safeParse(result)
    if (!parsed.success) {
      return Response.json({ error: "Voice worker returned an invalid session" }, { status: 502 })
    }

    const token = {
      provider: "workers-voice",
      token: parsed.data.value,
      expiresAt: parsed.data.expires_at * 1000,
      config: { providerOptions: { workerUrl } },
    } satisfies RealtimeToken

    return Response.json(token, { headers: { "Cache-Control": "no-store" } })
  } catch {
    return Response.json({ error: "Voice worker request failed" }, { status: 502 })
  }
}
