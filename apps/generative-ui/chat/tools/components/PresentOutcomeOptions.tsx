"use client"
import React from "react"
import { useChatContext } from "@/chat/client"
import { vocabulary } from "@/targets/face-value/vocabulary/en"
import { requestReferenceImage } from "../../messages/request-reference-image"
import { textPart } from "../../parts/text"
import type { PublicOutcome } from "@/outcomes"

type PresentOutcomeOptionsPart = {
  id: string;
  input?: { outcomes?: PublicOutcome[] };
}

export const PresentOutcomeOptions = ({ part }: { part: PresentOutcomeOptionsPart }) => {
  const { append } = useChatContext()
  const outcomes = [...(part.input?.outcomes ?? [])].sort((a, b) => a.order - b.order)

  const select = async (outcome: PublicOutcome) => {
    await append({
      id: crypto.randomUUID(),
      role: "user",
      parts: [
        textPart(vocabulary.messages.userPickedOutcome.replace("{title}", outcome.title)),
        {
          type: "tool-result",
          toolCallId: part.id,
          content: JSON.stringify({ outcomeId: outcome.id }),
          state: "complete",
        },
      ],
    })
    await append(requestReferenceImage(outcome.id))
  }

  return (
    <div className="mb-6 animate-in fade-in-50 slide-in-from-bottom-2 duration-400" aria-labelledby="selectOutcome">
      <div role="listbox" aria-label={vocabulary.messages.outcomesAria} aria-labelledby="selectOutcome" className="grid grid-cols-2 gap-2">
        <span id="selectOutcome" className="sr-only">{vocabulary.messages.selectOutcome}</span>
        {outcomes.map((outcome) => (
          <button
            key={outcome.id}
            role="option"
            type="button"
            aria-selected={false}
            aria-labelledby={outcome.id}
            onClick={() => select(outcome)}
            className="px-3 py-2 md:py-1 rounded border text-title bg-muted text-muted-foreground"
          >
            <span id={outcome.id} className="sr-only">{outcome.title}</span>
            {outcome.title}
          </button>
        ))}
      </div>
    </div>
  )
}
