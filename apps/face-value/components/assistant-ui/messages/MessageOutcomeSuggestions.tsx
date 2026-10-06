"use client";

import { MessagePrimitive } from "@assistant-ui/react";
import type { PublicOutcome } from "@/outcomes";

export function MessageOutcomeSuggestions({
  outcomes,
  onSelect,
  disabled,
  selectedOutcomeId,
}: {
  disabled: boolean;
  outcomes: PublicOutcome[];
  onSelect: (id: string) => void;
  selectedOutcomeId?: PublicOutcome["id"];
}) {
  return (
    <MessagePrimitive.Root className="mb-6 animate-in fade-in-50 slide-in-from-bottom-2 duration-300">
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
              className={
                isSelected
                  ? "px-3 py-2 md:py-1 rounded border bg-secondary text-secondary-foreground disabled:bg-muted disabled:text-muted-foreground text-title"
                  : "px-3 py-2 md:py-1 rounded border disabled:bg-muted disabled:text-muted-foreground text-title"
              }
            >
              {title}
            </button>
          );
        })}
      </div>
    </MessagePrimitive.Root>
  );
}
