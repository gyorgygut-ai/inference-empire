import type { useChatContext } from "@/chat/contexts"

type AddResult = Parameters<ReturnType<typeof useChatContext>["addToolResult"]>[0]

export function generationFailed(toolCallId: string, failure: { error: string }): AddResult {
  return {
    toolCallId,
    tool: "runGenerateImage",
    output: null,
    state: "output-error",
    errorText: failure.error,
  }
}
