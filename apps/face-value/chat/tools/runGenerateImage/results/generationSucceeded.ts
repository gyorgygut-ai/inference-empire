import type { useChatContext } from "@/chat/client"

type AddResult = Parameters<ReturnType<typeof useChatContext>["addToolResult"]>[0]

export function generationSucceeded(
  toolCallId: string,
  output: { presignedUrl: string },
): AddResult {
  return {
    toolCallId,
    tool: "runGenerateImage",
    output,
  }
}
