"use client"

import { MessagePrimitive } from "@assistant-ui/react"
import { vocabulary } from "@/lib/vocabulary"

export function MessageRejected() {
  return (
    <MessagePrimitive.Root className="mb-4">
      <p>{vocabulary.messages.rejected}</p>
    </MessagePrimitive.Root>
  )
}
