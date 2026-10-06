"use client"

import { MessagePrimitive } from "@assistant-ui/react"
import { vocabulary } from "@/messages/vocabulary"

export function MessageRejected() {
  return (
    <MessagePrimitive.Root className="mb-4 animate-in fade-in-50 slide-in-from-bottom-2 duration-300 bg-muted rounded-xl p-4">
      <p>{vocabulary.messages.rejected}</p>
    </MessagePrimitive.Root>
  )
}
