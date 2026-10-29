import "server-only"
import type { RealtimeToken } from "@tanstack/ai"

export async function POST() {
  const token = {
    provider: "workers-voice",
    token: crypto.randomUUID(),
    expiresAt: Date.now() + 15 * 60 * 1000,
    config: {},
  } satisfies RealtimeToken

  return Response.json(token, { headers: { "Cache-Control": "no-store" } })
}
