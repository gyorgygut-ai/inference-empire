"use client"

import { MessagePrimitive } from "@assistant-ui/react"
import { vocabulary } from "@/lib/vocabulary"

export function MessageUploadReference() {
  return (
    <MessagePrimitive.Root className="mb-4">
      <p className="mb-2">{vocabulary.messages.uploadReference}</p>
    </MessagePrimitive.Root>
  )
}
