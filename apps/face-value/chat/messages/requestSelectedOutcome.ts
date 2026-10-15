import type { UIMessage } from "@tanstack/ai-client"
import { vocabulary } from "@/chat/vocabulary/en"
import { textPart } from "../parts/text"
import type { PublicOutcome } from "@/outcomes"
import type { ChatOptions } from "../options"

type AppTools = ChatOptions["tools"]

export function requestSelectedOutcome(outcomes: PublicOutcome[] = []): UIMessage<AppTools> {
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
  } satisfies UIMessage<AppTools>
}