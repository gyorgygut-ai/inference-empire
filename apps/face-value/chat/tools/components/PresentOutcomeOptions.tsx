"use client";
import React from "react";
import { useChatContext } from "@/chat/client";
import { vocabulary } from "@/chat/vocabulary/en";
import { requestReferenceImage } from "../../messages/request-reference-image";

import type { ToolProps } from "@tanstack/ai-react/ui";
import type { ChatOptions } from "../../options";

type PresentOutcomeOptionsProps = ToolProps<
  ChatOptions,
  "presentOutcomeOptions"
>;

export const PresentOutcomeOptions = ({ part }: PresentOutcomeOptionsProps) => {
  const { append, addToolResult } = useChatContext();
  const outcomes = [...(part.input?.outcomes ?? [])].sort(
    (a, b) => a.order - b.order,
  );

  const select = async (outcome: (typeof outcomes)[number]) => {
    await addToolResult({
      toolCallId: part.id,
      tool: "presentOutcomeOptions",
      output: { outcomeId: outcome.id },
    });
    await append(requestReferenceImage(outcome.id));
  };

  return (
    <div
      className="mb-6 animate-in fade-in-50 slide-in-from-bottom-2 duration-400"
      aria-labelledby="selectOutcome"
    >
      <div
        role="listbox"
        aria-label={vocabulary.messages.outcomesAria}
        aria-labelledby="selectOutcome"
        className="grid grid-cols-2 gap-2"
      >
        <span id="selectOutcome" className="sr-only">
          {vocabulary.messages.selectOutcome}
        </span>
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
            <span id={outcome.id} className="sr-only">
              {outcome.title}
            </span>
            {outcome.title}
          </button>
        ))}
      </div>
    </div>
  );
};
