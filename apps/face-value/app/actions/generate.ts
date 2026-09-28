"use server"

import { createHash } from "crypto"
import sharp from "sharp"
import { workerRouterConfig } from "@/app/inference-api/router-config"
import { postQueue, pollQueue } from "@/app/inference-api/api"
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

  const config = {
    baseUrl: workerRouterConfig.baseUrl,
    token: workerRouterConfig.authToken,
    maxPollMillis: 5 * 60 * 1000,
    pollIntervalMillis: 3000,
  }

  try {
    const taskId = await postQueue(input, config)
    const { output } = await pollQueue(taskId, config)
    const res = await fetch(output.artifact.presigned_url)
    if (!res.ok) { throw new Error(vocabulary.feedback.workerError) }
    const arrayBuffer = await res.arrayBuffer()
    const value = { dataUrl: `data:image/png;base64,${Buffer.from(arrayBuffer).toString("base64")}` }
    cache.set(key, value)
    return value
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : ""
    if (msg.includes("REJECTED")) { throw new Error(vocabulary.feedback.rejected) }
    if (msg.includes("SERVER_TIMEOUT")) { throw new Error(vocabulary.feedback.timeout) }
    throw new Error(vocabulary.feedback.workerError)
  }
}
