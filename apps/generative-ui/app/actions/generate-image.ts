"use server"

import sharp from "sharp"
import { inferWithPolling } from "@inference/worker-router-client"
import { getInferenceOutcome } from "@/outcomes"

const MAX_SIZE = 512
const MAX_BYTES = 5 * 1024 * 1024

type GenerateImageInput = {
  outcomeId: string;
  base64: string;
  mimeType: string;
}

type GenerateImageResult = { presignedUrl: string } | { error: string }

type FluxOutput = {
  artifact: {
    presigned_url: string;
  };
}

export async function generateImageAction(input: GenerateImageInput): Promise<GenerateImageResult> {
  const baseUrl = process.env.GENERATE_IMAGE_SERVICE_URL ?? ""
  const token = process.env.GENERATE_IMAGE_SERVICE_SECRET_AUTH_TOKEN ?? ""
  if (!baseUrl || !token) {
    return { error: "Server misconfigured" }
  }

  const outcome = getInferenceOutcome(input.outcomeId)
  if (!outcome) {
    return { error: "Unknown outcome" }
  }

  if (!input.mimeType.startsWith("image/")) {
    return { error: "Reference image rejected" }
  }

  let resized: Buffer
  try {
    const raw = Buffer.from(input.base64, "base64")
    if (raw.length === 0 || raw.length > MAX_BYTES) {
      return { error: "Image exceeds size limit" }
    }
    resized = await sharp(raw)
      .resize({ width: MAX_SIZE, height: MAX_SIZE, fit: "inside" })
      .toBuffer()
  } catch {
    return { error: "Reference image rejected" }
  }

  try {
    const output = await inferWithPolling<FluxOutput>(
      {
        prompt: outcome.prompt,
        width: outcome.width,
        height: outcome.height,
        input_image: resized.toString("base64"),
      },
      {
        baseUrl,
        token,
        pollIntervalMs: 5000,
        timeoutMs: 180000,
      },
    )
    if (!output.artifact.presigned_url) {
      return { error: "The server rejected this request." }
    }
    return { presignedUrl: output.artifact.presigned_url }
  } catch (error) {
    return { error: error instanceof Error ? error.message : "The server rejected this request." }
  }
}
