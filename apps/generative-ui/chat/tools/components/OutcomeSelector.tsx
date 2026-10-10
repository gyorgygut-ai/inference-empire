"use client"
import React from "react"
import type { PublicOutcome } from "@/outcomes/outcomes"
import { vocabulary } from "@/messages"

export interface OutcomeSelectorProps {
  outcomes: PublicOutcome[]
  append: (message: { id: string; role: "user" | "assistant"; parts: any[] }) => void
}

export const OutcomeSelector = React.memo(function OutcomeSelector({
  outcomes,
  append,
}: OutcomeSelectorProps) {
  const { selectOutcome, userPickedOutcome } = vocabulary.messages

  return (
    <div className="mb-6 animate-in fade-in-50 slide-in-from-bottom-2 duration-400" aria-labelledby="selectOutcome">
      <div role="listbox" aria-label={vocabulary.messages.outcomesAria} aria-labelledby="selectOutcome" className="grid grid-cols-2 gap-2">
        <span id="selectOutcome" className="sr-only">{selectOutcome}</span>
        {outcomes.map(({ id: outcomeId, title }) => (
          <button
            key={outcomeId}
            role="option"
            type="button"
            aria-selected={false}
            aria-labelledby={outcomeId}
            onClick={async () => {
              await append({
                id: crypto.randomUUID(),
                role: "user",
                parts: [{ type: "text", content: userPickedOutcome.replace("{title}", title) }],
              })
              await append({
                id: crypto.randomUUID(),
                role: "assistant",
                parts: [
                  { type: "text", content: vocabulary.messages.uploadReference },
                  { type: "activity", activityType: "fileUpload", content: {} },
                ],
              })
            }}
            className="px-3 py-2 md:py-1 rounded border text-title bg-muted text-muted-foreground"
          >
            <span id={outcomeId} className="sr-only">{title}</span>
            {title}
          </button>
        ))}
      </div>
    </div>
  )
})