"use client";

import { MessagePrimitive } from "@assistant-ui/react";
import { vocabulary } from "@/messages/vocabulary";

export function MessageRequestInference({
  isPending,
  canGenerate,
  onGenerate: onGenerateAction,
}: {
  isPending: boolean;
  canGenerate: boolean;
  onGenerate: () => void;
}) {
  return (
    <MessagePrimitive.Root className="mb-4 animate-in fade-in-50 slide-in-from-bottom-2 duration-300 bg-muted rounded-xl p-4">
      <button
        type="button"
        onClick={onGenerateAction}
        disabled={!canGenerate || isPending}
        className="mt-2 px-4 py-2 bg-primary text-primary-foreground rounded disabled:opacity-50"
      >
        {vocabulary.messages.requestInference}
      </button>
    </MessagePrimitive.Root>
  );
}
