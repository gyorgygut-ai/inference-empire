"use client"

import { MessagePrimitive } from "@assistant-ui/react"
import { vocabulary } from "@/lib/vocabulary"

export function MessageRequestInference({
  generating,
  canGenerate,
  onGenerate,
}: {
  generating: boolean
  canGenerate: boolean
  onGenerate: () => void
}) {
  return (
    <MessagePrimitive.Root className="mb-4">
      <button
        type="button"
        onClick={onGenerate}
        disabled={!canGenerate || generating}
        className="mt-2 px-4 py-2 bg-primary text-primary-foreground rounded disabled:opacity-50"
      >
        {vocabulary.messages.requestInference}
      </button>
    </MessagePrimitive.Root>
  )
}
