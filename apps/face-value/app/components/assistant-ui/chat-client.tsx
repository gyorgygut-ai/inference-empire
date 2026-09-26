"use client"
import { AssistantRuntimeProvider, useLocalRuntime, type ChatModelAdapter } from "@assistant-ui/react"
import Thread from "./thread"
import { ChatProvider, useChat } from "./chat-context"
import { requestOutcome, type ActionResult } from "@/app/actions"

function getErrorMessage(error: string): string {
  switch (error) {
    case "SERVER_TIMEOUT":
      return "Server timed out. Please try again."
    case "OUTCOME_MISSING":
    case "OUTCOME_INVALID":
      return "Invalid outcome. Please select one."
    case "INPUT_IMAGE_MISSING":
      return "Please upload an image."
    case "INPUT_IMAGE_TOO_LARGE":
      return "Image too large. Please use a smaller file."
    case "INPUT_IMAGE_TYPE_NOT_ALLOWED":
      return "Invalid image format. Please use PNG or JPG."
    default:
      return "Something went wrong. Please try again."
  }
}

function buildFormData(imageData: string | undefined, outcomeId: string): FormData {
  const formData = new FormData()
  formData.append("outcomeId", outcomeId)

  if (imageData) {
    // Handle data URL: data:image/...;base64,...
    const commaIdx = imageData.indexOf(",")
    const base64Data = commaIdx > 0 ? imageData.slice(commaIdx + 1) : imageData
    const mimeTypeMatch = imageData.match(/^data:([^;]+);/)
    const mimeType = mimeTypeMatch ? mimeTypeMatch[1] : "image/png"
    const byteCharacters = atob(base64Data)
    const byteArrays: number[][] = []
    for (let offset = 0; offset < byteCharacters.length; offset += 512) {
      const slice = byteCharacters.slice(offset, offset + 512)
      byteArrays.push(Array.from(slice, (c) => c.charCodeAt(0)))
    }
    const blob = new Blob(byteArrays.map(arr => new Uint8Array(arr)), { type: mimeType })
    formData.append("image", blob, "image.png")
  }

  return formData
}

function createAdapter(selectedOutcomeId: string | null): ChatModelAdapter {
  return {
    async run({ messages }) {
      const lastUser = [...messages].reverse().find((m) => m.role === "user")
      if (!lastUser) {
        return { content: [{ type: "text" as const, text: "No message found" }] }
      }

      // Outcome ID comes from chat context (set by SuggestionPrimitive onClick)
      const outcomeId = selectedOutcomeId

      if (!outcomeId) {
        return { content: [{ type: "text" as const, text: "No outcome selected" }] }
      }

      // Extract image from message attachments
      const imageContent = lastUser.content.find(
        (c) => c.type === "image",
      ) as { image: string } | undefined
      const imageData = imageContent?.image

      try {
        const formData = buildFormData(imageData, outcomeId)
        const result: ActionResult = await requestOutcome(null, formData)

        if ("imageUrl" in result) {
          return {
            content: [{ type: "image" as const, image: result.imageUrl }],
          }
        }
        return {
          content: [{ type: "text" as const, text: getErrorMessage(result.error) }],
        }
      } catch {
        return {
          content: [{ type: "text" as const, text: "Failed to generate image" }],
        }
      }
    },
  }
}

export default function ChatClient({
  outcomes,
  serverOnline,
}: {
  outcomes: { id: string; title: string }[]
  serverOnline: boolean
}) {
  const { selectedOutcomeId } = useChat()
  const adapter = createAdapter(selectedOutcomeId)

  const runtime = useLocalRuntime(adapter, {
    initialMessages: serverOnline
      ? []
      : [
          {
            id: "offline",
            role: "system" as const,
            content: [{ type: "text" as const, text: "❌ Server offline" }],
            createdAt: new Date(),
          },
        ],
  })

  return (
    <ChatProvider>
      <AssistantRuntimeProvider runtime={runtime}>
        <Thread outcomes={outcomes} serverOnline={serverOnline} />
      </AssistantRuntimeProvider>
    </ChatProvider>
  )
}
