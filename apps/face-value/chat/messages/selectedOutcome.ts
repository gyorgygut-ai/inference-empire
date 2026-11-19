import type { UIMessage } from "@tanstack/ai-client"
import { textPart } from "../parts/text"
import type { ChatOptions } from "../options"

type AppTools = ChatOptions["tools"]

export function selectedOutcome(title: string): UIMessage<AppTools> {
  return {
    id: crypto.randomUUID(),
    role: "user",
    parts: [textPart(title)],
  }
}
