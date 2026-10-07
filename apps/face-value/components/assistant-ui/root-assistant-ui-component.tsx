"use client";

import React, { useEffect } from "react";
import { useAui, useAuiState, ThreadPrimitive } from "@assistant-ui/react";
import type { PublicOutcome } from "@/outcomes";
import { useImageGeneration } from "../image-generation/image-generation";
import { MessageSwitch } from "./message-switch";
import { UploadComposer } from "./upload-composer";
import { createMessage, ChatPhase } from "./chat";

export const RootAssistantUiComponent = ({
  outcomes,
}: {
  outcomes: PublicOutcome[];
}) => {
  const aui = useAui();
  const messages = useAuiState((s) => s.thread.messages);
  const threadReady = useAuiState((s) => !s.thread.isLoading);
  const attachments = useAuiState((s) => s.thread.composer.attachments);
  const referenceFile =
    attachments.find((a) => a.type === "image" && a.file)?.file ?? null;

  const {
    selectedOutcome,
    result,
    isPending,
    canGenerate,
    onSelectOutcome,
    onGenerate,
  } = useImageGeneration(outcomes, referenceFile);

  useEffect(() => {
    if (!threadReady || messages.length !== 0) {
      return;
    }

    aui.thread.append(createMessage(ChatPhase.PROMPT_FOR_OUTCOME));
  }, [threadReady, messages.length, aui]);

  return (
    <ThreadPrimitive.Root className="h-full flex flex-col">
      <ThreadPrimitive.Viewport className="flex-1 overflow-y-auto">
        <ThreadPrimitive.Messages>
          {({ message }) => (
            <MessageSwitch
              message={message}
              outcomes={outcomes}
              selectedOutcome={selectedOutcome}
              isPending={isPending}
              canGenerate={canGenerate}
              onSelectOutcome={onSelectOutcome}
              onGenerate={onGenerate}
              artifactUrl={
                result?.status === "done" ? result.presignedUrl : undefined
              }
            />
          )}
        </ThreadPrimitive.Messages>
      </ThreadPrimitive.Viewport>
      <UploadComposer _selectedOutcomeId={selectedOutcome?.id} />
    </ThreadPrimitive.Root>
  );
};
