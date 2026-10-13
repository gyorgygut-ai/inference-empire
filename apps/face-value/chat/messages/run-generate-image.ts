import type { UIMessage, MessagePart } from "@tanstack/ai-client"
import { vocabulary } from "@/targets/face-value/vocabulary/en"
import { textPart } from "../parts/text"
import type { ChatOptions } from "../options"

type Tools = ChatOptions["tools"]

export function requestGenerateImage(input: { outcomeId: string; base64: string; mimeType: string }): UIMessage<Tools> {
  const parts: MessagePart<Tools>[] = [
    textPart(vocabulary.runGenerateImage.requested.assistantMessage),
    {
      type: "tool-call",
      id: crypto.randomUUID(),
      name: "runGenerateImage",
      arguments: JSON.stringify(input),
      input,
      state: "approval-requested",
      approval: {
        id: crypto.randomUUID(),
        needsApproval: true,
      },
    },
  ]
  return {
    id: crypto.randomUUID(),
    role: "assistant",
    parts,
  }
}
