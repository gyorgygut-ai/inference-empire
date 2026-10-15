"use client"
import React from "react"
import clsx from "clsx"
import { useChatContext } from "@/chat/client"
import { selectOutcome } from "../../../thread"
import type { ToolProps } from "@tanstack/ai-react/ui"
import type { ChatOptions } from "../../../options"

type OutcomePart = ToolProps<ChatOptions, "presentOutcomeOptions">["part"]
type Outcome = NonNullable<OutcomePart["input"]>["outcomes"][number]
type ChatApi = ReturnType<typeof useChatContext>

export const OutcomeOptionButton = ({
  chat,
  part,
  outcome,
  selected,
  disabled,
}: {
  chat: ChatApi
  part: OutcomePart
  outcome: Outcome
  selected: boolean
  disabled: boolean
}) => {
  const handleSelect = () => {
    if (!disabled) {
      selectOutcome(chat, part, outcome)
    }
  }

  return (
    <button
      role="option"
      type="button"
      aria-selected={selected}
      aria-labelledby={outcome.id}
      onClick={handleSelect}
      disabled={disabled}
      className={clsx("px-3 py-2 md:py-1 text-md rounded border text-title", {
        "bg-muted text-muted-foreground": !selected,
        "bg-primary text-primary-foreground": selected,
      })}
    >
      {outcome.title}
    </button>
  )
}
