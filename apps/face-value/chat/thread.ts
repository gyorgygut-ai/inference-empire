"use client"
import { requestReferenceImage } from "./messages/requestReferenceImage"
import { runGenerateImage } from "./messages/runGenerateImage"
import { outcomeSelected } from "./tools/presentOutcomeOptions/results/outcomeSelected"
import { referenceUploaded } from "./tools/presentImageUpload/results/referenceUploaded"
import { generationSucceeded } from "./tools/runGenerateImage/results/generationSucceeded"
import { generationFailed } from "./tools/runGenerateImage/results/generationFailed"
import { generateImageAction } from "@/app/actions/generate-image"
import { findLastToolCall, isGenerationLocked } from "./findLastToolCall"
import type { useChatContext } from "@/chat/client"
import type { ToolProps } from "@tanstack/ai-react/ui"
import type { ChatOptions } from "./options"

type ChatApi = Pick<
  ReturnType<typeof useChatContext>,
  "messages" | "append" | "addToolResult" | "addToolApprovalResponse"
>

type OutcomeSelection = ToolProps<ChatOptions, "presentOutcomeOptions">["part"]
type UploadCall = ToolProps<ChatOptions, "presentImageUpload">["part"]
type GenerationCall = ToolProps<ChatOptions, "runGenerateImage">["part"]

const readFileAsData = (file: File): Promise<{ base64: string; mimeType: string }> =>
  new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(new Error("Reference image unreadable"))
    reader.onload = () => {
      const url = String(reader.result ?? "")
      const match = /^data:([\w/-]+);base64,(.+)$/.exec(url)
      if (!match) {
        reject(new Error("Reference image unreadable"))
        return
      }
      resolve({ base64: match[2], mimeType: match[1] })
    }
    reader.readAsDataURL(file)
  })

export const selectOutcome = async (
  chat: ChatApi,
  part: OutcomeSelection,
  outcome: { id: string },
): Promise<void> => {
  if (isGenerationLocked(chat.messages)) {
    return
  }
  await chat.addToolResult(outcomeSelected(part.id, outcome))
  const hasUpload = chat.messages.some((message) =>
    message.parts.some((p) => p.type === "tool-call" && p.name === "presentImageUpload"),
  )
  if (!hasUpload) {
    await chat.append(requestReferenceImage(outcome.id))
  }
}

export const uploadReference = async (
  chat: ChatApi,
  part: UploadCall,
  file: File,
): Promise<void> => {
  if (isGenerationLocked(chat.messages)) {
    return
  }
  const selected = findLastToolCall(chat.messages, "presentOutcomeOptions")
  const selectedId =
    selected && selected.type === "tool-call" && selected.name === "presentOutcomeOptions"
      ? selected.output?.outcomeId
      : undefined
  const outcomeId = selectedId ?? part.input?.outcomeId
  if (!outcomeId) {
    return
  }
  const data = await readFileAsData(file)
  await chat.addToolResult(referenceUploaded(part.id, data))
  const hasGeneration = chat.messages.some((message) =>
    message.parts.some((p) => p.type === "tool-call" && p.name === "runGenerateImage"),
  )
  if (!hasGeneration) {
    await chat.append(runGenerateImage({ outcomeId, base64: data.base64, mimeType: data.mimeType }))
  }
}

export const approveGeneration = async (
  chat: ChatApi,
  part: GenerationCall,
): Promise<void> => {
  const approval = part.approval
  const input = part.input
  if (!approval || !input) {
    return
  }
  await chat.addToolApprovalResponse({ id: approval.id, approved: true })
  const generation = await generateImageAction(input)
  await chat.addToolResult(
    "presignedUrl" in generation
      ? generationSucceeded(part.id, generation)
      : generationFailed(part.id, generation),
  )
}
