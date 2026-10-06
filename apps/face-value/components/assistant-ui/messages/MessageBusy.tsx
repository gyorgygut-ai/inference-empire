"use client"

import { MessagePrimitive } from "@assistant-ui/react"
import { vocabulary } from "@/messages/vocabulary"

export function MessageBusy({ width, height }: { width: number; height: number }) {
  return (
    <MessagePrimitive.Root className="mb-4 animate-in fade-in-50 slide-in-from-bottom-2 duration-300 bg-muted rounded-xl p-4">
      <p className="mb-2">{vocabulary.messages.busy}</p>
      <p className="mb-2 text-sm text-muted-foreground">Waiting on inference…</p>
      <div
        role="status"
        aria-label={vocabulary.messages.busy}
        style={{ aspectRatio: `${width} / ${height}` }}
        className="w-full animate-pulse rounded-lg bg-muted/80"
      />
    </MessagePrimitive.Root>
  )
}