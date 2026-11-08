import "server-only"
import { config } from "@/config"
import { createSessionResponse } from "./createSessionResponse"

export async function POST() {
  return createSessionResponse(
    config.voiceWorkerUrl,
    config.voiceWorkerAuthToken,
  )
}
