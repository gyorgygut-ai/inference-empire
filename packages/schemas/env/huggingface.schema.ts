import { z } from "zod"

export const api = z.object({ "SECRET_HUGGINGFACE_TOKEN": z.string().min(1) })
export type Api = z.infer<typeof api>
