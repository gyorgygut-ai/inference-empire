import { UIMessage } from "@tanstack/ai"
import { vocabulary } from "@/targets/face-value/vocabulary/en"
import { textPart } from "../parts/text"
import type { PublicOutcome } from "@/outcomes"

export function requestSelectedOutcome(outcomes: PublicOutcome[] = []) {
  return {
    id: "select-outcome",
    role: "assistant",
    parts: [
      textPart(vocabulary.requestSelectedOutcome.assistantMessage),
      {
        type: "tool-call",
        id: crypto.randomUUID(),
        name: "presentOutcomeOptions",
        arguments: JSON.stringify({}),
        input: { outcomes },
        state: "input-complete",
      },
    ],
  } satisfies UIMessage
}
