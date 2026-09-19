import type { Flux2Klein9bInput, TinySdInput } from "@inference/types"

export type RouterContract = "flux2_klein9b" | "tiny_sd"
export type RouterInput = Flux2Klein9bInput | TinySdInput

export function parseQueueBody(body: unknown, contract: string): RouterInput | null {
  if (typeof body !== "object" || body === null) return null
  const rec = body as Record<string, unknown>
  const input: unknown = rec["input"]
  if (typeof input !== "object" || input === null) return null
  const prompt: unknown = (input as Record<string, unknown>)["prompt"]
  if (typeof prompt !== "string" || prompt.length === 0) return null
  if (contract !== "flux2_klein9b" && contract !== "tiny_sd") return null
  return input as RouterInput
}
