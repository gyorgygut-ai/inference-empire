import type { UIMessage, MessagePart } from "@tanstack/ai-client"
import { vocabulary } from "@packages/ui/chat/vocabulary/en"
import { textPart } from "../parts/text"
import type { ChatOptions } from "../options"

type Tools = ChatOptions["tools"]

export function requestReferenceImage(outcomeId: string): UIMessage<Tools> {
  const parts: MessagePart<Tools>[] = [
    textPart(vocabulary.requestReferenceImage.assistantMessage),
    {
      type: "tool-call",
      id: crypto.randomUUID(),
      name: "presentImageUpload",
      arguments: JSON.stringify({ outcomeId }),
      input: { outcomeId },
      state: "input-complete",
    },
  ]
  return {
    id: crypto.randomUUID(),
    role: "assistant",
    parts,
  }
}