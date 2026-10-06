"use server"

import { createHash } from "crypto"
import sharp from "sharp"
import { inferWithPolling } from "@inference/worker-router-client"
import type { Flux2Klein9BOutput } from "@/app/inference-api/schema"
import { workerRouterConfig } from "@/app/inference-api/router-config"
import { getInferenceOutcome } from "@/outcomes"
import { vocabulary } from "@/lib/vocabulary"

const MAX_SIZE = 512
const MAX_BYTES = 5 * 1024 * 1024

const cache = new Map<string, { dataUrl: string }>()

function cacheKey(outcomeId: string, base64: string): string {
  return `${outcomeId}:${createHash("sha256").update(base64).digest("hex")}`
}

export async function generateImage(outcomeId: string, imageFile: File) {
  if (!imageFile) {
    throw new Error(vocabulary.feedback.missingImage)
  }
  if (imageFile.size > MAX_BYTES) {
    throw new Error(vocabulary.feedback.sizeLimit)
  }
  if (!imageFile.type.startsWith("image/")) {
    throw new Error(vocabulary.feedback.sizeLimit)
  }

  const buffer = Buffer.from(await imageFile.arrayBuffer())
  const resized = await sharp(buffer).resize({ width: MAX_SIZE, height: MAX_SIZE, fit: "inside" }).toBuffer()
  const base64 = resized.toString("base64")

  const outcome = getInferenceOutcome(outcomeId)
  if (!outcome) {
    throw new Error(vocabulary.feedback.workerError)
  }

  const key = cacheKey(outcomeId, base64)
  const hit = cache.get(key)
  if (hit) { return hit }

  const input = {
    prompt: outcome.prompt,
    width: outcome.width,
    height: outcome.height,
    input_image: base64,
  }

  try {
    const output = await inferWithPolling<Flux2Klein9BOutput>(input, {
      baseUrl: workerRouterConfig.baseUrl,
      token: workerRouterConfig.authToken,
      pollIntervalMs: 3000,
      timeoutMs: 50 * 1000,
    })
    const res = await fetch(output.artifact.presigned_url)
    if (!res.ok) { throw new Error(vocabulary.feedback.workerError) }
    const arrayBuffer = await res.arrayBuffer()
    const value = { dataUrl: `data:image/png;base64,${Buffer.from(arrayBuffer).toString("base64")}` }
    cache.set(key, value)
    return value
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : ""
    if (msg.includes("failed") || msg.includes("cancelled")) { throw new Error(vocabulary.feedback.rejected) }
    if (msg.includes("timeout after")) { throw new Error(vocabulary.feedback.timeout) }
    throw new Error(vocabulary.feedback.workerError)
  }
}
