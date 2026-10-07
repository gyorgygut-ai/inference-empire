"use client";

import type { MessageState } from "@assistant-ui/react";
import React from "react";
import type { PublicOutcome } from "@/outcomes";
import { ChatPhase } from "./chat";
import { MessageSelectOutcome } from "./messages/MessageSelectOutcome";
import { MessageUploadReference } from "./messages/MessageUploadReference";
import { MessageOutcomeSuggestions } from "./messages/MessageOutcomeSuggestions";
import { MessageRequestInference } from "./messages/MessageRequestInference";
import { MessageArtifact } from "./messages/MessageArtifact";

export const MessageSwitch = ({
  message,
  outcomes,
  selectedOutcome,
  isPending,
  canGenerate,
  onSelectOutcome,
  onGenerate,
  artifactUrl,
}: {
  message: MessageState;
  outcomes: PublicOutcome[];
  selectedOutcome: PublicOutcome | null;
  isPending: boolean;
  canGenerate: boolean;
  onSelectOutcome: (id: string) => void;
  onGenerate: () => void;
  artifactUrl?: string;
}) => {
  const meta = message.metadata as { custom?: { type?: string } } | undefined;
  const type = meta?.custom?.type;

  if (type === ChatPhase.PROMPT_FOR_OUTCOME) {
    return (
      <>
        <MessageSelectOutcome />
        <MessageOutcomeSuggestions
          outcomes={outcomes}
          disabled={isPending}
          onSelect={onSelectOutcome}
          selectedOutcomeId={selectedOutcome?.id}
        />
      </>
    );
  }
  if (type === ChatPhase.PROMPT_FOR_REFERENCE) {
    return <MessageUploadReference />;
  }
  if (type === ChatPhase.REQUEST_INFERENCE) {
    return (
      <MessageRequestInference
        onGenerateAction={onGenerate}
        disabled={isPending || !canGenerate}
      />
    );
  }
  if ([ChatPhase.INFERENCE_BUSY, ChatPhase.INFERENCE_REJECTED, ChatPhase.INFERENCE_FULFILLED].includes(type as ChatPhase)) {
    return (
      <MessageArtifact
        state={type as ChatPhase}
        image={artifactUrl}
        width={selectedOutcome?.width}
        height={selectedOutcome?.height}
      />
    );
  }

  return null;
};
