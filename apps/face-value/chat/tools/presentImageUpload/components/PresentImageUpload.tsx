"use client"
import React from "react"
import { useChatContext } from "@/chat/client"
import { vocabulary } from "@/chat/vocabulary/en"
import { uploadReference } from "../../../thread"
import { isGenerationLocked } from "../../../findLastToolCall"
import type { ToolProps } from "@tanstack/ai-react/ui"
import type { ChatOptions } from "../../../options"

type PresentImageUploadProps = ToolProps<ChatOptions, "presentImageUpload">

export const PresentImageUpload = ({ part }: PresentImageUploadProps) => {
  const chat = useChatContext()
  const inputRef = React.useRef<HTMLInputElement>(null)
  const outcomeId = part.input?.outcomeId
  const locked = isGenerationLocked(chat.messages)
  const disabled = !outcomeId || locked
  const preview = part.output

  const handleOpen = () => {
    if (!disabled) {
      inputRef.current?.click()
    }
  }

  const handleChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!disabled && file) {
      await uploadReference(chat, part, file)
    }
    if (inputRef.current) {
      inputRef.current.value = ""
    }
  }

  return (
    <div className="mb-4 animate-in fade-in-50 slide-in-from-bottom-2 duration-500 bg-surface italic rounded-xl p-4" aria-labelledby="uploadReference">
      <span id="uploadReference" className="sr-only">{vocabulary.messages.uploadReference}</span>
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        hidden
        disabled={disabled}
        onChange={handleChange}
      />
      <button
        type="button"
        onClick={handleOpen}
        disabled={disabled}
        className="w-full px-4 py-3 border-2 border-dashed rounded-xl hover:bg-primary/5 transition-colors"
      >
        <div className="flex items-center justify-center gap-2 text-sm text-secondary-foreground">📎 {""} {vocabulary.messages.uploadCta}</div>
      </button>
      {preview ? (
        <img
          src={`data:${preview.mimeType};base64,${preview.base64}`}
          alt={vocabulary.messages.resultAlt}
          className="mt-3 w-full rounded-xl"
        />
      ) : null}
    </div>
  )
}
