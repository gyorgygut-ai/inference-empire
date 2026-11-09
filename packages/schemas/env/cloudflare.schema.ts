import { z } from "zod"

export const api = z.object({ "SECRET_CLOUDFLARE_ACCOUNT_ID": z.string().min(1), "SECRET_CLOUDFLARE_API_TOKEN": z.string().min(1), "SECRET_CLOUDFLARE_R2_API_TOKEN": z.string().min(1) })
export type Api = z.infer<typeof api>
