import type { useChatContext } from "@/chat/client"

type AddResult = Parameters<ReturnType<typeof useChatContext>["addToolResult"]>[0]

export function outcomeSelected(toolCallId: string, outcome: { id: string }): AddResult {
  return {
    toolCallId,
    tool: "presentOutcomeOptions",
    output: { outcomeId: outcome.id },
  }
}
