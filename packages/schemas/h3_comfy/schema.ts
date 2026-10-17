import { z } from "zod"

export const api = z.object({ "input": z.object({ "prompt": z.string(), "width": z.number().int().default(1344), "height": z.number().int().default(768), "length": z.number().int().default(124), "steps": z.number().int().default(20), "seed": z.union([z.number().int(), z.null()]).default(null), "first_frame": z.union([z.string(), z.null()]).default(null), "last_frame": z.union([z.string(), z.null()]).default(null) }), "output": z.object({ "artifact": z.object({ "presigned_url": z.string() }) }) })
export type Api = z.infer<typeof api>
