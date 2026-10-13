"use client"
import React from "react"
import { useChatContext } from "@/chat/client"
import { vocabulary } from "@packages/ui/chat/vocabulary/en"
import { requestGenerateImage } from "../../messages/run-generate-image"
import { imagePart } from "../parts/image"
import type { ToolProps } from "@tanstack/ai-react/ui"
import type { ChatOptions } from "../../options"

type PresentImageUploadProps = ToolProps<ChatOptions, "presentImageUpload">

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

export const PresentImageUpload = ({ part }: PresentImageUploadProps) => {
  const { append, addToolResult } = useChatContext()
  const inputRef = React.useRef<HTMLInputElement>(null)
  const outcomeId = part.input?.outcomeId

  const upload = async (file: File) => {
    if (!outcomeId) {
      return
    }
    const data = await readFileAsData(file)
    await append({
      id: crypto.randomUUID(),
      role: "user",
      parts: [imagePart(data.base64, data.mimeType)],
    })
    await addToolResult({
      toolCallId: part.id,
      tool: "presentImageUpload",
      output: { base64: data.base64, mimeType: data.mimeType },
    })
    await append(requestGenerateImage({ outcomeId, base64: data.base64, mimeType: data.mimeType }))
  }

  return (
    <div className="mb-4 animate-in fade-in-50 slide-in-from-bottom-2 duration-500 bg-surface italic rounded-xl p-4" aria-labelledby="uploadReference">
      <span id="uploadReference" className="sr-only">{vocabulary.messages.uploadReference}</span>
      {vocabulary.messages.uploadReference}
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        hidden
        disabled={!outcomeId}
        onChange={async (e) => {
          const file = e.target.files?.[0]
          if (file) {
            await upload(file)
          }
          if (inputRef.current) {
            inputRef.current.value = ""
          }
        }}
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        disabled={!outcomeId}
        className="w-full px-4 py-3 border-2 border-dashed rounded-xl hover:bg-primary/5 transition-colors"
      >
        <div className="flex items-center justify-center gap-2 text-sm text-secondary-foreground">📎 {""} {vocabulary.messages.uploadCta}</div>
      </button>
    </div>
  )
}