"use client"

import { MessagePrimitive } from "@assistant-ui/react"
import { vocabulary } from "@/lib/vocabulary"

export function MessageBusy({ width, height }: { width: number; height: number }) {
  return (
    <MessagePrimitive.Root className="mb-4">
      <p className="mb-2">{vocabulary.messages.busy}</p>
      <div
        role="status"
        aria-label={vocabulary.messages.busy}
        style={{ aspectRatio: `${width} / ${height}` }}
        className="w-full animate-pulse rounded-lg bg-muted"
      />
    </MessagePrimitive.Root>
  )
}
