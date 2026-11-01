"use client"
import React from "react"
import clsx from "clsx"
import type { ToolProps } from "@tanstack/ai-react/ui"
import type { ChatOptions } from "../../../options"

type OutcomePart = ToolProps<ChatOptions, "presentOutcomeOptions">["part"]
type Outcome = NonNullable<OutcomePart["input"]>["outcomes"][number]

export const OutcomeOptionButton = ({
  outcome,
  selected,
  disabled,
  onSelect,
}: {
  outcome: Outcome
  selected: boolean
  disabled: boolean
  onSelect: () => void
}) => {
  return (
    <button
      role="option"
      type="button"
      aria-selected={selected}
      aria-labelledby={outcome.id}
      onClick={onSelect}
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
