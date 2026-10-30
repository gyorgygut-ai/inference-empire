import { z } from "zod"

export const api = z.object({ "SECRET_R2_ENDPOINT": z.string().url().min(1), "SECRET_R2_BUCKET": z.string().min(1), "SECRET_R2_ACCESS_KEY": z.string().min(1), "SECRET_R2_SECRET_KEY": z.string().min(1) })
export type Api = z.infer<typeof api>
