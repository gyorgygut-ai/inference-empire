import "server-only"
import sharp from "sharp"
import { BaseImageAdapter, type ImageAdapterConfig } from "@tanstack/ai/adapters"
import type { ImageGenerationOptions, ImageGenerationResult } from "@tanstack/ai"
import { inferWithPolling } from "@inference/worker-router-client"
import type { Flux2Klein9BOutput } from "@/app/inference-api/schema"
import { workerRouterConfig } from "@/app/inference-api/router-config"
import { getInferenceOutcome } from "@/outcomes/inference-outcomes"

const MAX_SIZE = 512
const MAX_BYTES = 5 * 1024 * 1024

const dataUrlPattern = /^data:([\w/-]+);base64,(.+)$/

const toBase64 = (value: string): { base64: string; mimeType: string } => {
  const match = dataUrlPattern.exec(value)
  if (match) {
    return { base64: match[2], mimeType: match[1] }
  }
  return { base64: value, mimeType: "image/png" }
}

export class Flux2KleinAdapter extends BaseImageAdapter {
  readonly name = "flux2-klein"
  readonly model = "flux-2-klein" as const

  constructor(config: ImageAdapterConfig = {}) {
    super("flux-2-klein", config)
  }

  async generateImages(options: ImageGenerationOptions): Promise<ImageGenerationResult> {
    const outcomeId = (options.modelOptions as { outcomeId?: string } | undefined)?.outcomeId
    const outcome = outcomeId ? getInferenceOutcome(outcomeId) : null
    if (!outcome) {
      throw new Error("Unknown outcome")
    }

    const parts = Array.isArray(options.prompt) ? options.prompt : []
    const imagePart = parts.find((p) => p.type === "image")
    const source = (imagePart as { source?: { type: string; value?: unknown; mimeType?: string } } | undefined)?.source
    if (!source || source.type === "file" || typeof source.value !== "string") {
      throw new Error("Reference image required")
    }

    let reference: { base64: string; mimeType: string }
    if (source.type === "data") {
      reference = toBase64(source.value)
    } else if (source.type === "url") {
      const fetched = await fetch(source.value)
      const blob = await fetched.blob()
      if (!blob.type.startsWith("image/") || blob.size > MAX_BYTES) {
        throw new Error("Reference image rejected")
      }
      const buffer = Buffer.from(await blob.arrayBuffer())
      reference = { base64: buffer.toString("base64"), mimeType: blob.type }
    } else {
      throw new Error("Reference image required")
    }

    const resized = await sharp(Buffer.from(reference.base64, "base64"))
      .resize({ width: MAX_SIZE, height: MAX_SIZE, fit: "inside" })
      .toBuffer()

    const output = await inferWithPolling<Flux2Klein9BOutput>(
      {
        prompt: outcome.prompt,
        width: outcome.width,
        height: outcome.height,
        input_image: resized.toString("base64"),
      },
      {
        baseUrl: workerRouterConfig.baseUrl,
        token: workerRouterConfig.authToken,
        pollIntervalMs: 5000,
        timeoutMs: 180000,
      },
    )

    return {
      id: crypto.randomUUID(),
      model: this.model,
      images: [{ url: output.artifact.presigned_url }],
    }
  }
}

export const flux2KleinAdapter = new Flux2KleinAdapter()
