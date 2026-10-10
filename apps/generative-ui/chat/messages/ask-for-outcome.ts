import { UIMessage } from "@tanstack/ai"
import { vocabulary } from "@/messages"
import { textPart } from "../parts/text"

export function assistantMessagePromptForOutcome() {
  return {
    id: "select-outcome",
    role: "assistant",
    parts: [textPart(vocabulary.messages.selectOutcome)],
  } satisfies UIMessage
}
