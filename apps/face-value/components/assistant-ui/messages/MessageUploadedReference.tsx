"use client"

import { MessagePrimitive, AttachmentPrimitive, useAui } from "@assistant-ui/react"
import { ImageIcon, XIcon } from "lucide-react"
import { useEffect, useState } from "react"

export function MessageUploadedReference({ 
  attachment, 
  messageId 
}: { 
  attachment: File | null; 
  messageId: string 
}) {
  const aui = useAui()
  const [previewUrl, setPreviewUrl] = useState<string>("")

  useEffect(() => {
    if (attachment && attachment instanceof File) {
      const url = URL.createObjectURL(attachment)
      setPreviewUrl(url)
      return () => URL.revokeObjectURL(url)
    }
  }, [attachment])

  const handleRemove = () => {
    aui.thread.removeMessage(messageId)
  }

  return (
    <MessagePrimitive.Root className="mb-4 animate-in fade-in-50 slide-in-from-bottom-2 duration-300">
      <div className="rounded-xl border-2 border-dashed border-border p-4 w-full">
        <AttachmentPrimitive.Root className="flex items-center gap-2 rounded-lg border p-2">
          <div className="flex size-10 items-center justify-center overflow-hidden rounded bg-muted text-xs">
            {previewUrl ? (
              <img src={previewUrl} className="size-full object-cover" alt="Thumb" />
            ) : (
              <ImageIcon className="size-4" />
            )}
          </div>
          <span className="min-w-0 flex-1 truncate text-sm">
            {attachment?.name || "Reference Image"}
          </span>
          <button 
            type="button"
            onClick={handleRemove}
            className="ml-auto rounded-full p-1 hover:bg-muted"
          >
            <XIcon className="size-3" />
          </button>
        </AttachmentPrimitive.Root>
      </div>
    </MessagePrimitive.Root>
  )
}
