import { z } from "zod"

export const api = z.object({ "input": z.object({ "audio": z.string().meta({"description":"Base64 pcm16 mono audio input"}), "sample_rate": z.number().int().default(24000), "voice": z.string(), "language": z.string().default("en") }), "output": z.object({ "audio": z.string().meta({"description":"Base64 pcm16 mono reply audio"}), "transcript": z.string(), "sample_rate": z.number().int().default(24000) }) })
export type Api = z.infer<typeof api>
