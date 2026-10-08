"use client"
import React, { useRef } from "react"
import { vocabulary } from "@/messages"
import { readFileAsData } from "./file-utils"

export interface FileUploadPartProps {
  append: (message: { id: string; role: "user" | "assistant"; parts: any[] }) => void
}

export const FileUploadPart = React.memo(function FileUploadPart({ append }: FileUploadPartProps) {
  const inputRef = useRef<HTMLInputElement>(null)

  return (
    <div className="mb-4 animate-in fade-in-50 slide-in-from-bottom-2 duration-500 bg-surface italic rounded-xl p-4" aria-labelledby="uploadReference">
      <span id="uploadReference" className="sr-only">{vocabulary.messages.uploadReference}</span>
      {vocabulary.messages.uploadReference}
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        hidden
        onChange={async (e) => {
          const file = e.target.files?.[0]
          if (file) {
            const data = await readFileAsData(file)
            await append({
              id: crypto.randomUUID(),
              role: "user",
              parts: [{ type: "image", source: { type: "data", value: data.base64, mimeType: data.mimeType } }],
            })
            await append({
              id: crypto.randomUUID(),
              role: "assistant",
              parts: [
                { type: "text", content: vocabulary.messages.requestInference },
                { type: "activity", activityType: "submitButton", content: {} },
              ],
            })
          }
          if (inputRef.current) {
            inputRef.current.value = ""
          }
        }}
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        className="w-full px-4 py-3 border-2 border-dashed rounded-xl hover:bg-primary/5 transition-colors"
      >
        <div className="flex items-center justify-center gap-2 text-sm text-secondary-foreground">📎 {""} {vocabulary.messages.uploadCta}</div>
      </button>
    </div>
  )
})