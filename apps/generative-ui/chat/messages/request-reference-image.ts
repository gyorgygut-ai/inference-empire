import { UIMessage } from "@tanstack/ai"
import { vocabulary } from "@/targets/face-value/vocabulary/en"
import { textPart } from "../parts/text"

export function requestReferenceImage(outcomeId: string) {
  return {
    id: crypto.randomUUID(),
    role: "assistant",
    parts: [
      textPart(vocabulary.requestReferenceImage.assistantMessage),
      {
        type: "tool-call",
        id: crypto.randomUUID(),
        name: "presentImageUpload",
        arguments: JSON.stringify({ outcomeId }),
        input: { outcomeId },
        state: "input-complete",
      },
    ],
  } satisfies UIMessage
}
