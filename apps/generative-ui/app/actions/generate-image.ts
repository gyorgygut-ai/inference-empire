"use server"

import sharp from "sharp"
import { inferWithPolling } from "@inference/task-queue-client"
import { getInferenceOutcome } from "@/outcomes"
import type { Flux2Klein9BInput, Flux2Klein9BOutput } from "@/generated/router_flux2_api"

const MAX_SIZE = 512
const MAX_BYTES = 5 * 1024 * 1024

type GenerateImageInput = {
  outcomeId: string;
  base64: string;
  mimeType: string;
}

type GenerateImageResult = { presignedUrl: string } | { error: string }

export async function generateImageAction(input: GenerateImageInput): Promise<GenerateImageResult> {
  const baseUrl = process.env.ROUTER_FLUX2_APP_URL ?? ""
  const token = process.env.ROUTER_FLUX2_SECRET_AUTH_TOKEN ?? ""
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
    const request: Flux2Klein9BInput = {
      prompt: outcome.prompt,
      width: outcome.width,
      height: outcome.height,
      input_image: resized.toString("base64"),
    }
    const output = await inferWithPolling<Flux2Klein9BInput, Flux2Klein9BOutput>(
      request,
      {
        baseUrl,
        token,
        pollIntervalMs: 5000,
        timeoutMs: 180000,
      },
    )
    const url = output.artifact?.presigned_url
    if (!url) {
      return { error: "The server rejected this request." }
    }
    return { presignedUrl: url }
  } catch (error) {
    return { error: error instanceof Error ? error.message : "The server rejected this request." }
  }
}
