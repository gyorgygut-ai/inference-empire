import type { UIMessage, MessagePart } from "@tanstack/ai-client"
import { vocabulary } from "@/chat/vocabulary/en"
import { textPart } from "../parts/text"
import type { ChatOptions } from "../options"

type Tools = ChatOptions["tools"]

type GenerationInput = { outcomeId: string; base64: string; mimeType: string }
type GenerationState = "approval-requested" | "input-complete"

export function runGenerateImage(
  input: GenerationInput,
  toolCallId: string,
  state: GenerationState,
): UIMessage<Tools> {
  const id = crypto.randomUUID()
  if (state === "approval-requested") {
    const parts: MessagePart<Tools>[] = [
      textPart(vocabulary.runGenerateImage.requested.assistantMessage),
      {
        type: "tool-call",
        id: toolCallId,
        name: "runGenerateImage",
        arguments: JSON.stringify(input),
        input,
        state,
        approval: {
          id: crypto.randomUUID(),
          needsApproval: true,
        },
      },
    ]
    return { id, role: "assistant", parts }
  }
  const parts: MessagePart<Tools>[] = [
    {
      type: "tool-call",
      id: toolCallId,
      name: "runGenerateImage",
      arguments: JSON.stringify(input),
      input,
      state,
    },
  ]
  return { id, role: "assistant", parts }
}
