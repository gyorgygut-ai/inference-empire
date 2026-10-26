import { z } from "zod"

export const api = z.object({ "input": z.object({ "prompt": z.string(), "reference_image": z.union([z.string(), z.null()]).default(null), "height": z.number().int().default(768), "width": z.number().int().default(768), "num_inference_steps": z.number().int().default(8), "guidance_scale": z.number().default(0), "seed": z.union([z.number().int(), z.null()]).default(null), "lora_scale": z.number().default(1), "face_crop": z.boolean().default(true) }), "output": z.object({ "artifact": z.object({ "presigned_url": z.string() }) }) })
export type Api = z.infer<typeof api>
