import { useChatContext } from "./chat-client"
import type { PublicOutcome } from "@/outcomes/outcomes"
import { vocabulary } from "@/messages"

export const useChatFlow = (outcomes: PublicOutcome[]) => {
  const { messages } = useChatContext()

  // Derived purely from thread (thread owns all state)
  const selectedOutcomeId = [...messages].reverse().reduce<string | undefined>((found, m) => {
    if (found || m.role !== "user") { return found }
    const textPart = m.parts?.find((p) => p.type === "text")
    const content = (textPart as { content?: string })?.content
    const match = outcomes.find((o) => content === vocabulary.messages.userPickedOutcome.replace("{title}", o.title))
    return match?.id ?? found
  }, undefined)

  const reference = [...messages].reverse().reduce<{ base64: string; mimeType: string } | undefined>((found, m) => {
    if (found || m.role !== "user") { return found }
    const imagePart = m.parts?.find((p) => p.type === "image") as { source?: { type: string; value?: unknown; mimeType?: string } } | undefined
    const source = imagePart?.source
    if (!source || typeof source.value !== "string") { return found }
    if (source.type === "data") { return { base64: source.value, mimeType: source.mimeType ?? "image/png" } }
    return found
  }, undefined)

  return { selectedOutcomeId, reference }
}