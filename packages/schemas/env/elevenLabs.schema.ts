import { z } from "zod"

export const api = z.object({ "SECRET_ELEVENLABS_API_KEY": z.string().min(1), "SECRET_ELEVENLABS_AGENT_ID": z.string().min(1) })
export type Api = z.infer<typeof api>
