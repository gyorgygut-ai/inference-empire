"use client"
import React from "react"
import { useChatContext } from "@/chat/client"
import { generateImageAction } from "@/app/actions/generate-image"
import { vocabulary } from "@/targets/face-value/vocabulary/en"
import { textPart } from "../../parts/text"
import { Spinner } from "./Spinner"
import { GenerateImageArtifact } from "./GenerateImageArtifact"

type RunGenerateImagePart = {
  id: string;
  state: string;
  input?: {
    outcomeId?: string;
    base64?: string;
    mimeType?: string;
  };
}

type RunGenerateImageResult = {
  toolCallId: string;
  content: string | Array<{ type: string }>;
  state: string;
}

const presignedUrlFrom = (result?: RunGenerateImageResult): string | null => {
  if (!result || result.state !== "complete" || typeof result.content !== "string") {
    return null
  }
  try {
    const parsed: unknown = JSON.parse(result.content)
    if (
      typeof parsed === "object" &&
      parsed !== null &&
      "presignedUrl" in parsed &&
      typeof parsed.presignedUrl === "string"
    ) {
      return parsed.presignedUrl
    }
    return null
  } catch {
    return null
  }
}

export const GenerateImageApproval = ({
  part,
  result,
}: {
  part: RunGenerateImagePart;
  result?: RunGenerateImageResult;
}) => {
  const { append } = useChatContext()

  if (part.state === "awaiting-input" || part.state === "input-streaming") {
    return <Spinner />
  }

  const url = presignedUrlFrom(result)
  if (url) {
    return <GenerateImageArtifact url={url} />
  }
  if (result && result.state === "error") {
    return (
      <p className="my-2 text-sm italic" aria-labelledby="errorRejected">
        <span id="errorRejected" className="sr-only">{vocabulary.runGenerateImage.error.assistantMessage}</span>
        {vocabulary.runGenerateImage.error.assistantMessage}
      </p>
    )
  }
  if (part.state === "approval-responded") {
    return <p className="my-2 text-sm italic">{vocabulary.runGenerateImage.responded.assistantMessage}</p>
  }

  const ready = Boolean(part.input?.outcomeId && part.input?.base64 && part.input?.mimeType)

  const approve = async () => {
    const outcomeId = part.input?.outcomeId
    const base64 = part.input?.base64
    const mimeType = part.input?.mimeType
    if (!outcomeId || !base64 || !mimeType) {
      return
    }
    await append({
      id: crypto.randomUUID(),
      role: "assistant",
      parts: [textPart(vocabulary.runGenerateImage.streaming.assistantMessage)],
    })
    const generation = await generateImageAction({ outcomeId, base64, mimeType })
    if ("presignedUrl" in generation) {
      await append({
        id: crypto.randomUUID(),
        role: "assistant",
        parts: [
          textPart(vocabulary.runGenerateImage.responded.assistantMessage),
          {
            type: "tool-result",
            toolCallId: part.id,
            content: JSON.stringify({ presignedUrl: generation.presignedUrl }),
            state: "complete",
          },
        ],
      })
    } else {
      await append({
        id: crypto.randomUUID(),
        role: "assistant",
        parts: [
          {
            type: "tool-result",
            toolCallId: part.id,
            content: generation.error,
            state: "error",
            error: generation.error,
          },
        ],
      })
    }
  }

  return (
    <div className="mb-4 animate-in fade-in-50 slide-in-from-bottom-2 duration-400">
      <button
        type="button"
        onClick={approve}
        disabled={!ready}
        aria-labelledby="approveGeneration"
        className="my-2 px-4 py-3 bg-primary text-primary-foreground rounded w-full"
      >
        <span id="approveGeneration" className="sr-only">{vocabulary.runGenerateImage.requested.userApprove}</span>
        {vocabulary.runGenerateImage.requested.userApprove}
      </button>
    </div>
  )
}
