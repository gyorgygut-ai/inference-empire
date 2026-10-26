import { z } from "zod"

export const api = z.object({ "input": z.object({ "prompt": z.string(), "height": z.number().int().default(512), "width": z.number().int().default(512), "guidance_scale": z.number().default(1), "num_inference_steps": z.number().int().default(4), "seed": z.union([z.number().int(), z.null()]).default(null), "input_image": z.union([z.string(), z.null()]).default(null), "reference_images": z.array(z.string()).default([]) }), "output": z.object({ "artifact": z.object({ "presigned_url": z.string() }) }) })
export type Api = z.infer<typeof api>
