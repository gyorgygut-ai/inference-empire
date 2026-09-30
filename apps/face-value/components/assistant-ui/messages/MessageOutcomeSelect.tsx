"use client"

import { MessagePrimitive } from "@assistant-ui/react"
import { vocabulary } from "@/lib/vocabulary"
import type { PublicOutcome } from "@/outcomes"

export function MessageOutcomeSelect({
  outcomes,
  selectedId,
  onSelect,
}: {
  outcomes: PublicOutcome[]
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  return (
    <MessagePrimitive.Root className="mb-4 animate-in fade-in-50 slide-in-from-bottom-2 duration-300 bg-muted rounded-xl p-4">
      <p className="mb-2">{vocabulary.messages.selectOutcome}</p>
      <div className="mt-2 flex gap-2 flex-wrap" role="listbox" aria-label="Outcomes">
        {outcomes.map((o) => {
          const selected = o.id === selectedId
          return (
            <button
              key={o.id}
              type="button"
              role="option"
              aria-selected={selected}
              onClick={() => onSelect(o.id)}
              className={
                selected
                  ? "px-3 py-1 rounded border bg-primary text-primary-foreground"
                  : "px-3 py-1 rounded border"
              }
            >
              {o.title}
            </button>
          )
        })}
      </div>
    </MessagePrimitive.Root>
  )
}
