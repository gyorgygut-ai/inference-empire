import type { UIMessage } from "@tanstack/ai-client"
import { imagePart } from "../parts/image"
import type { ChatOptions } from "../options"

type AppTools = ChatOptions["tools"]

export function referenceImage(data: {
  base64: string
  mimeType: string
}): UIMessage<AppTools> {
  return {
    id: crypto.randomUUID(),
    role: "user",
    parts: [imagePart(data.base64, data.mimeType)],
  }
}
