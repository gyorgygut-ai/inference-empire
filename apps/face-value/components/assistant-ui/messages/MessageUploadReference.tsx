"use client"

import { MessagePrimitive, useAui } from "@assistant-ui/react"
import { vocabulary } from "@/messages/vocabulary"
import { useRef } from "react"

export function MessageUploadReference() {
  const aui = useAui()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleButtonClick = () => {
    fileInputRef.current?.click()
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    aui.thread.append({
      role: "user",
      content: [{ type: "text", text: file.name }],
      metadata: { 
        custom: { type: "uploaded-reference" },
        attachment: file 
      },
    })
  }

  return (
    <MessagePrimitive.Root className="mb-4 animate-in fade-in-50 slide-in-from-bottom-2 duration-300 bg-muted rounded-xl p-4">
      <p className="mb-2">{vocabulary.messages.uploadReference}</p>
      
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept="image/*"
        className="hidden"
      />
      
      <button 
        type="button"
        onClick={handleButtonClick}
        className="mt-2 inline-block cursor-pointer rounded border px-3 py-1 text-sm hover:bg-muted"
      >
        {vocabulary.messages.uploadReference}
      </button>
    </MessagePrimitive.Root>
  )
}
