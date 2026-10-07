"use client";

import React from "react";
import { MessagePrimitive } from "@assistant-ui/react";
import { cn } from "cn";
import type { PublicOutcome } from "@/outcomes";

export const MessageOutcomeSuggestions = ({
  outcomes,
  onSelect,
  disabled,
  selectedOutcomeId,
}: {
  disabled: boolean;
  outcomes: PublicOutcome[];
  onSelect: (id: string) => void;
  selectedOutcomeId?: PublicOutcome["id"];
}) => (
  <MessagePrimitive.Root className="mb-6 animate-in fade-in-50 slide-in-from-bottom-2 duration-400">
    <div
      role="listbox"
      aria-label="Outcomes"
      className="grid grid-cols-2 gap-2"
    >
      {outcomes.map(({ id: outcomeId, title }) => {
        const isSelected = outcomeId === selectedOutcomeId;

        return (
          <button
            role="option"
            type="button"
            key={outcomeId}
            disabled={disabled}
            aria-selected={isSelected}
            onClick={() => onSelect(outcomeId)}
            className={cn({
              "px-3 py-2 md:py-1 rounded border text-title": true,
              "bg-secondary text-secondary-foreground": isSelected,
              "bg-muted text-muted-foreground": !isSelected && !disabled,
              "cursor-not-allowed opacity-50": disabled,
            })}
          >
            {title}
          </button>
        );
      })}
    </div>
  </MessagePrimitive.Root>
);