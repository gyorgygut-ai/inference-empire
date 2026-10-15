"use client"
import React from "react"
import { vocabulary } from "@/chat/vocabulary/en"
import type { ToolProps } from "@tanstack/ai-react/ui"
import type { ChatOptions } from "../../../options"
import { Spinner } from "./Spinner"
import { GenerateImageArtifact } from "./GenerateImageArtifact"
import { GenerateImageApproval } from "./GenerateImageApproval"

type RunGenerateImageProps = ToolProps<ChatOptions, "runGenerateImage">

export const GenerateImageTool = ({ part, result }: RunGenerateImageProps) => {
  if (part.state === "awaiting-input" || part.state === "input-streaming") {
    return <Spinner />
  }
  if (part.state === "approval-requested") {
    return <GenerateImageApproval part={part} />
  }
  if (part.state === "error") {
    const detail = result?.error?.trim() ? result.error : vocabulary.runGenerateImage.error.assistantMessage
    return (
      <p className="my-2 text-sm italic" aria-labelledby="errorRejected">
        <span id="errorRejected" className="sr-only">{detail}</span>
        {detail}
      </p>
    )
  }
  if (part.output?.presignedUrl) {
    return <GenerateImageArtifact url={part.output.presignedUrl} />
  }
  if (part.state === "approval-responded") {
    return (
      <div className="my-2 flex items-center gap-2" role="status">
        <span className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        <span className="text-sm italic">{vocabulary.runGenerateImage.responded.assistantMessage}</span>
      </div>
    )
  }
  return null
}