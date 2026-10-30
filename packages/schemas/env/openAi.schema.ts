import { z } from "zod"

export const api = z.object({ "SECRET_OPENAI_API_KEY": z.string().min(1) })
export type Api = z.infer<typeof api>
