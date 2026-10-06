"use client";

import { useState, useTransition } from "react";
import { useAui } from "@assistant-ui/react";
import type { PublicOutcome } from "@/outcomes";
import { generateImage } from "@/app/actions/generate";
import { createMessage, ChatPhase } from "../assistant-ui/chat";

export function useImageGeneration(
  outcomes: PublicOutcome[],
  referenceFile: File | null,
) {
  const aui = useAui();
  const [selectedOutcome, setSelectedOutcome] = useState<PublicOutcome | null>(
    null,
  );
  const [generationResponse, setGenerationResponse] =
    useState<Awaited<ReturnType<typeof generateImage>>>();
  const [isPending, startTransition] = useTransition();

  const canGenerate = !!selectedOutcome && !!referenceFile;

  const onSelectOutcome = (id: string) => {
    setGenerationResponse(undefined);
    setSelectedOutcome(outcomes.find((o) => o.id === id) ?? null);

    const messages = aui.thread.getState().messages;
    const hasPromptedForReference = messages.some(
      (m) =>
        (m.metadata as { custom?: { type?: string } } | undefined)?.custom
          ?.type === ChatPhase.PROMPT_FOR_REFERENCE,
    );

    if (!hasPromptedForReference) {
      aui.thread.append(createMessage(ChatPhase.PROMPT_FOR_REFERENCE));
    }
  };

  const onGenerate = async () => {
    const isUseful = selectedOutcome && referenceFile && !isPending;

    if (!isUseful) {
      return;
    }

    aui.thread.append(createMessage(ChatPhase.INFERENCE_BUSY));

    startTransition(async () => {
      try {
        const response = await generateImage(selectedOutcome.id, referenceFile);

        setGenerationResponse(response);

        return aui.thread.append(
          createMessage(
            response.status === "rejected"
              ? ChatPhase.INFERENCE_REJECTED
              : ChatPhase.INFERENCE_FULFILLED,
          ),
        );
      } catch {
        aui.thread.append(createMessage(ChatPhase.INFERENCE_REJECTED));
      }
    });
  };

  return {
    isPending,
    onGenerate,
    canGenerate,
    onSelectOutcome,
    selectedOutcome,
    result: generationResponse,
  };
}
