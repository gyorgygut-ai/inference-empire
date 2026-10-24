import { z } from "zod"

export const api = z.object({ "input": z.object({ "prompt": z.string(), "negative_prompt": z.string().default(""), "height": z.number().int().default(512), "width": z.number().int().default(512), "num_inference_steps": z.number().int().default(20), "guidance_scale": z.number().default(7.5), "seed": z.union([z.number().int(), z.null()]).default(null) }), "output": z.object({ "artifact": z.object({ "presigned_url": z.string() }) }) })
export type Api = z.infer<typeof api>
