"use server"

import sharp from "sharp"
import { workerRouterConfig } from "@/app/inference-api/router-config"
import { postQueue, pollQueue } from "@/app/inference-api/api"
import { getInferenceOutcome } from "@/outcomes"

const MAX_SIZE = 512
const MAX_BYTES = 5 * 1024 * 1024

export async function generateImage(outcomeId: string, imageFile: File) {
  if (!imageFile) {
    throw new Error("Reference image missing")
  }
  if (imageFile.size > MAX_BYTES) {
    throw new Error("Reference image exceeds size limit")
  }
  if (!imageFile.type.startsWith("image/")) {
    throw new Error("Invalid image format")
  }

  const buffer = Buffer.from(await imageFile.arrayBuffer())
  const resized = await sharp(buffer).resize({ width: MAX_SIZE, height: MAX_SIZE, fit: "inside" }).toBuffer()
  const base64 = resized.toString("base64")

  const outcome = getInferenceOutcome(outcomeId)
  if (!outcome) {
    throw new Error("Outcome not found")
  }

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

  const taskId = await postQueue(input, config)
  const { output } = await pollQueue(taskId, config)

  const res = await fetch(output.artifact.presigned_url)
  const arrayBuffer = await res.arrayBuffer()

  return { dataUrl: `data:image/png;base64,${Buffer.from(arrayBuffer).toString("base64")}` }
}
