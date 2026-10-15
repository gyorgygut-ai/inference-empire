import type { useChatContext } from "@/chat/client"

type AddResult = Parameters<ReturnType<typeof useChatContext>["addToolResult"]>[0]

export function referenceUploaded(
  toolCallId: string,
  data: { base64: string; mimeType: string },
): AddResult {
  return {
    toolCallId,
    tool: "presentImageUpload",
    output: { base64: data.base64, mimeType: data.mimeType },
  }
}
