import { z } from "zod"

export const api = z.object({ "SECRET_MODAL_TOKEN_ID": z.string().min(1), "SECRET_MODAL_TOKEN_SECRET": z.string().min(1) })
export type Api = z.infer<typeof api>
