"use client"
import React from "react"
import { useChatContext } from "@/chat/client"
import { generateImageAction } from "@/app/actions/generate-image"
import { vocabulary } from "@/chat/vocabulary/en"
import { textPart } from "../../parts/text"
import type { ToolProps } from "@tanstack/ai-react/ui"
import type { ChatOptions } from "../../options"

type ApprovalPart = ToolProps<ChatOptions, "runGenerateImage">["part"]

export const GenerateImageApproval = ({ part }: { part: ApprovalPart }) => {
  const { append, addToolApprovalResponse, addToolResult } = useChatContext()
  const approval = part.approval
  const input = part.input

  if (!approval || !input) {
    return null
  }

  const approve = async () => {
    await addToolApprovalResponse({ id: approval.id, approved: true })
    await append({
      id: crypto.randomUUID(),
      role: "assistant",
      parts: [textPart(vocabulary.runGenerateImage.streaming.assistantMessage)],
    })
    const generation = await generateImageAction(input)
    if ("presignedUrl" in generation) {
      await addToolResult({
        toolCallId: part.id,
        tool: "runGenerateImage",
        output: generation,
      })
    } else {
      await addToolResult({
        toolCallId: part.id,
        tool: "runGenerateImage",
        output: null,
        state: "output-error",
        errorText: generation.error,
      })
    }
  }

  return (
    <div className="mb-4 animate-in fade-in-50 slide-in-from-bottom-2 duration-400">
      <button
        type="button"
        onClick={approve}
        aria-labelledby="approveGeneration"
        className="my-2 px-4 py-3 bg-primary text-primary-foreground rounded w-full"
      >
        <span id="approveGeneration" className="sr-only">{vocabulary.runGenerateImage.requested.userApprove}</span>
        {vocabulary.runGenerateImage.requested.userApprove}
      </button>
    </div>
  )
}