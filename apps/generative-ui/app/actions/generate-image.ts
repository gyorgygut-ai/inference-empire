"use server"

import { generateImage, type ImageGenerationResult } from "@tanstack/ai"
import { flux2KleinAdapter } from "@/chat/adapters/flux2-adapter"

type ImagePartSource = { type: string; value?: unknown; mimeType?: string }
type PromptPart = { type: string; content?: string; source?: ImagePartSource }

export async function generateImageAction(input: {
  prompt: string | PromptPart[];
  modelOptions?: { outcomeId?: string };
}): Promise<ImageGenerationResult> {
  return generateImage({
    adapter: flux2KleinAdapter,
    prompt: input.prompt as never,
    modelOptions: input.modelOptions as never,
  })
}
