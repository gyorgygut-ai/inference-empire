import { UIMessage } from "@tanstack/ai"
import { vocabulary } from "@/messages"

export function assistantMessagePromptForOutcome() {
  return {
    id: "select-outcome",
    role: "assistant",
    parts: [
      {
        type: "text",
        content: vocabulary.messages.selectOutcome,
      },
    ],
    // metadata: { outcomes },
    // parts: [
    //   { type: "text", content: vocabulary.messages.selectOutcome },
    //   {
    //     type: "activity",
    //     activityType: "outcomeSelector",
    //     content: { outcomes },
    //   },
    // ],
  } satisfies UIMessage
}
