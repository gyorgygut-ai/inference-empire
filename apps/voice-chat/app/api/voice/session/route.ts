import "server-only"
import { createSessionResponse } from "./createSessionResponse"

export async function POST() {
  return createSessionResponse(process.env.WORKER_URL, process.env.SECRET_BEAM_TOKEN)
}
