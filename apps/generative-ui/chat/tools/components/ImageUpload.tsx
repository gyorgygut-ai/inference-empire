"use client"
import React from "react"
import { useChatContext } from "@/chat/client"
import { vocabulary } from "@/targets/face-value/vocabulary/en"
import { imagePart } from "../../parts/image"
import { textPart } from "../../parts/text"

type ImageUploadPart = {
  id: string;
  input?: {
    outcomeId?: string;
  };
}

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

export const ImageUpload = ({ part }: { part: ImageUploadPart }) => {
  const { append } = useChatContext()
  const inputRef = React.useRef<HTMLInputElement>(null)

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
          const outcomeId = part.input?.outcomeId
          if (file && outcomeId) {
            const data = await readFileAsData(file)
            await append({
              id: crypto.randomUUID(),
              role: "user",
              parts: [
                imagePart(data.base64, data.mimeType),
                {
                  type: "tool-result",
                  toolCallId: part.id,
                  content: JSON.stringify({ base64: data.base64, mimeType: data.mimeType }),
                  state: "complete",
                },
              ],
            })
            await append({
              id: crypto.randomUUID(),
              role: "assistant",
              parts: [
                textPart(vocabulary.runGenerateImage.requested.assistantMessage),
                {
                  type: "tool-call",
                  id: crypto.randomUUID(),
                  name: "runGenerateImage",
                  arguments: JSON.stringify({ outcomeId, base64: data.base64, mimeType: data.mimeType }),
                  input: { outcomeId, base64: data.base64, mimeType: data.mimeType },
                  state: "approval-requested",
                  approval: {
                    id: crypto.randomUUID(),
                    needsApproval: true,
                  },
                },
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
}
