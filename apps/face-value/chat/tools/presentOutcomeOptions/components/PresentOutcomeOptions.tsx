"use client";
import React from "react";
import { useChatContext } from "@/chat/client";
import { vocabulary } from "@/chat/vocabulary/en";

import type { ToolProps } from "@tanstack/ai-react/ui";
import type { ChatOptions } from "../../../options";
import { isGenerationLocked } from "../../../findLastToolCall";
import { OutcomeOptionButton } from "./OutcomeOptionButton";

type PresentOutcomeOptionsProps = ToolProps<
  ChatOptions,
  "presentOutcomeOptions"
>;

export const PresentOutcomeOptions = ({ part }: PresentOutcomeOptionsProps) => {
  const chat = useChatContext();
  const { messages } = chat;
  const outcomes = [...(part.input?.outcomes ?? [])].sort(
    (a, b) => a.order - b.order,
  );
  const selectedOutcomeId = part.output?.outcomeId || null;
  const locked = isGenerationLocked(messages);

  return (
    <div
      className="animate-in fade-in-50 slide-in-from-bottom-2 duration-400"
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
          <OutcomeOptionButton
            key={outcome.id}
            chat={chat}
            part={part}
            outcome={outcome}
            selected={selectedOutcomeId === outcome.id}
            disabled={locked}
          />
        ))}
      </div>
    </div>
  );
};
