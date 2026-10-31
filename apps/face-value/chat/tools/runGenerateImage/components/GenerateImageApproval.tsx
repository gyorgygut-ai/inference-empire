"use client"
import React from "react"
import { useChatContext } from "@/chat/client"
import { approveGeneration } from "../../../thread"
import { vocabulary } from "@/chat/vocabulary/en"
import type { ToolProps } from "@tanstack/ai-react/ui"
import type { ChatOptions } from "../../../options"

type ApprovalPart = ToolProps<ChatOptions, "runGenerateImage">["part"]

export const GenerateImageApproval = ({ part }: { part: ApprovalPart }) => {
  const chat = useChatContext()
  const approval = part.approval
  const input = part.input

  const handleApprove = () => approveGeneration(chat, part)

  if (!approval || !input) {
    return null
  }

  return (
    <div className="animate-in fade-in-50 slide-in-from-bottom-2 duration-400">
      <button
        type="button"
        onClick={handleApprove}
        aria-labelledby="approveGeneration"
        className="my-2 px-4 py-3 bg-primary text-primary-foreground rounded w-full"
      >
        <span id="approveGeneration" className="sr-only">{vocabulary.runGenerateImage.requested.userApprove}</span>
        {vocabulary.runGenerateImage.requested.userApprove}
      </button>
    </div>
  )
}
