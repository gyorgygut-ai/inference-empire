"use client"
import React from "react"
import { vocabulary } from "@/targets/face-value/vocabulary/en"
import type { ToolProps } from "@tanstack/ai-react/ui"
import type { ChatOptions } from "../../options"
import { Spinner } from "./Spinner"
import { GenerateImageArtifact } from "./GenerateImageArtifact"
import { GenerateImageApproval } from "./GenerateImageApproval"

type RunGenerateImageProps = ToolProps<ChatOptions, "runGenerateImage">

export const GenerateImageTool = ({ part }: RunGenerateImageProps) => {
  if (part.state === "awaiting-input" || part.state === "input-streaming") {
    return <Spinner />
  }
  if (part.state === "approval-requested") {
    return <GenerateImageApproval part={part} />
  }
  if (part.state === "error") {
    return (
      <p className="my-2 text-sm italic" aria-labelledby="errorRejected">
        <span id="errorRejected" className="sr-only">{vocabulary.runGenerateImage.error.assistantMessage}</span>
        {vocabulary.runGenerateImage.error.assistantMessage}
      </p>
    )
  }
  if (part.output?.presignedUrl) {
    return <GenerateImageArtifact url={part.output.presignedUrl} />
  }
  if (part.state === "approval-responded") {
    return <p className="my-2 text-sm italic">{vocabulary.runGenerateImage.responded.assistantMessage}</p>
  }
  return null
}
