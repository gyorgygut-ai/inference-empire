"use server"

import sharp from "sharp"
import { postQueue, pollQueue, type InferenceConfig, type Flux2Klein9BInput } from "@/app/inference-api/api"
import { workerRouterConfig } from "@/app/inference-api/router-config"
import { getInferenceOutcome } from "@/outcomes"

const MAX_IMAGE_SIZE = 512 * 512 * 1024 // 512KB
const MAX_DIMENSION = 512

const inferenceConfig: InferenceConfig = {
  baseUrl: workerRouterConfig.baseUrl,
  token: workerRouterConfig.authToken,
  maxPollMillis: 300_000,
  pollIntervalMillis: 3000,
}

export async function runInference(imageBase64: string, outcomeId: string): Promise<{ url: string } | { error: string }> {
  // Validate
  const base64Data = imageBase64.split(",")[1] ?? imageBase64
  const buffer = Buffer.from(base64Data, "base64")

  if (buffer.length > MAX_IMAGE_SIZE) {
    return { error: "Image exceeds size limit." }
  }

  // Resize to max 512x512
  let resizedBase64: string
  try {
    const resized = await sharp(buffer)
      .resize(MAX_DIMENSION, MAX_DIMENSION, { fit: "inside", withoutEnlargement: true })
      .jpeg({ quality: 80 })
      .toBuffer()
    resizedBase64 = resized.toString("base64")
  } catch {
    return { error: "Failed to process image." }
  }

  // Get outcome
  const outcome = getInferenceOutcome(outcomeId)
  if (!outcome) {
    return { error: "Invalid outcome selected." }
  }

  // Run inference
  const input: Flux2Klein9BInput = {
    prompt: outcome.prompt,
    width: outcome.width,
    height: outcome.height,
    input_image: resizedBase64,
  }

  try {
    const taskId = await postQueue(input, inferenceConfig)
    const result = await pollQueue(taskId, inferenceConfig)

    return { url: result.output.artifact.presigned_url }
  } catch {
    return { error: "Inference failed. Please try again." }
  }
}