import "server-only"
import { createSessionResponse } from "./createSessionResponse"

export async function POST() {
  return createSessionResponse(
    process.env.SECRET_WORKER_URL,
    process.env.GENERATED_VOICE_WORKER_AUTH_TOKEN,
  )
}
