"use client"
import { useMemo } from "react"
import { AssistantRuntimeProvider, useLocalRuntime, AuiConfig, Suggestions, SimpleImageAttachmentAdapter, type ChatModelAdapter } from "@assistant-ui/react"
import { Thread } from "@/components/assistant-ui/elements/thread.aui"
import { ChatProvider, useChat } from "./chat-context"
import OutcomeWelcome from "./outcome-welcome"
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

function resolvePromptToId(text: string | null, outcomes: readonly { id: string, title: string }[]): string | null {
  if (!text) {
    return null
  }
  const match = outcomes.find((o) => o.id === text || o.title === text)
  return match ? match.id : text
}

function resolveOutcomeId(
  messages: readonly { role: string, content: readonly { type: string, text?: string }[] }[],
  outcomes: readonly { id: string, title: string }[],
  fallback: string | null,
): string | null {
  const lastUser = [...messages].reverse().find((m) => m.role === "user")
  const textPart = lastUser?.content.find((c) => c.type === "text" && c.text?.trim())
  const text = textPart?.text?.trim() ?? null
  if (text) {
    const match = outcomes.find((o) => o.id === text || o.title === text)
    if (match) {
      return match.id
    }
    return text
  }
  return resolvePromptToId(fallback, outcomes)
}

function resolveImageData(messages: readonly { role: string, content: readonly { type: string, image?: string }[] }[]): string | undefined {
  const reversed = [...messages].reverse()
  for (const m of reversed) {
    if (m.role !== "user") {
      continue
    }
    const found = m.content.find((c) => c.type === "image" && c.image) as { image: string } | undefined
    if (found?.image) {
      return found.image
    }
  }
  return undefined
}

function createAdapter(selectedOutcomeId: string | null, outcomes: readonly { id: string, title: string }[], onImage: (data: string) => void): ChatModelAdapter {
  return {
    async run({ messages }) {
      const lastUser = [...messages].reverse().find((m) => m.role === "user")
      if (!lastUser) {
        return { content: [{ type: "text" as const, text: "No message found" }] }
      }

      const outcomeId = resolveOutcomeId(messages, outcomes, selectedOutcomeId)

      if (!outcomeId) {
        return { content: [{ type: "text" as const, text: "No outcome selected" }] }
      }

      const imageData = resolveImageData(messages)
      if (imageData) {
        onImage(imageData)
      }

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

function ChatRuntime({ outcomes }: { outcomes: { id: string, title: string }[] }) {
  const { selectedOutcomeId, setLastImageData } = useChat()
  const adapter = useMemo(() => createAdapter(selectedOutcomeId, outcomes, setLastImageData), [selectedOutcomeId, outcomes, setLastImageData])
  const runtime = useLocalRuntime(adapter, {
    initialMessages: [],
    adapters: {
      attachments: new SimpleImageAttachmentAdapter(),
    },
  })
  const config = useMemo(() => AuiConfig({
    suggestions: Suggestions(outcomes.map((o) => ({ title: o.title, label: o.title, prompt: o.title }))),
  }), [outcomes])

  return (
    <AssistantRuntimeProvider runtime={runtime} config={config}>
      <Thread components={{ Welcome: OutcomeWelcome }} />
    </AssistantRuntimeProvider>
  )
}

export default function ChatClient({
  outcomes,
}: {
  outcomes: { id: string, title: string }[]
}) {
  return (
    <ChatProvider>
      <ChatRuntime outcomes={outcomes} />
    </ChatProvider>
  )
}
