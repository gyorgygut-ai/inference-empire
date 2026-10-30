import { z } from "zod"

export const api = z.object({ "VERCEL_TOKEN": z.string().min(1), "VERCEL_ORG_ID": z.string().min(1), "VERCEL_PROJECT_ID": z.string().min(1) })
export type Api = z.infer<typeof api>
