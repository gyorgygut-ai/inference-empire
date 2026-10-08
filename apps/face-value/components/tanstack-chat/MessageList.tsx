"use client";

import React from "react";
import { MessageSelectOutcome } from "../chat/messages/MessageSelectOutcome";
import { MessageUploadReference } from "../chat/messages/MessageUploadReference";
import { MessageOutcomeSuggestions } from "../chat/messages/MessageOutcomeSuggestions";
import { MessageRequestInference } from "../chat/messages/MessageRequestInference";
import { MessageArtifact } from "../chat/messages/MessageArtifact";
import { ChatPhase } from "../chat/chat";
import { useChatContext } from "./ChatProvider";

export const MessageList = () => {
  const {
    messages,
    outcomes,
    selectedOutcome,
    isLoading,
    canGenerate,
    artifactUrl,
    getMessagePhase,
    onSelectOutcome,
    triggerGeneration,
  } = useChatContext();

  return (
    <div className="flex-1 overflow-y-auto space-y-4 pb-4">
      {messages.map((message) => {
        const type = getMessagePhase(message.id);
        const content = message.parts?.find(
          (p: { type: string; content: string }) => p.type === "text"
        )?.content;

        if (type === ChatPhase.PROMPT_FOR_OUTCOME) {
          return (
            <React.Fragment key={message.id}>
              <MessageSelectOutcome />
              <MessageOutcomeSuggestions
                outcomes={outcomes}
                disabled={isLoading}
                onSelect={onSelectOutcome}
                selectedOutcomeId={selectedOutcome?.id}
              />
            </React.Fragment>
          );
        }
        if (type === ChatPhase.PROMPT_FOR_REFERENCE) {
          return <MessageUploadReference key={message.id} />;
        }
        if (type === ChatPhase.REQUEST_INFERENCE) {
          return (
            <MessageRequestInference
              key={message.id}
              onGenerateAction={triggerGeneration}
              disabled={isLoading || !canGenerate}
            />
          );
        }
        if (
          [
            ChatPhase.INFERENCE_BUSY,
            ChatPhase.INFERENCE_REJECTED,
            ChatPhase.INFERENCE_FULFILLED,
          ].includes(type as ChatPhase)
        ) {
          return (
            <MessageArtifact
              key={message.id}
              state={type as ChatPhase}
              content={content}
              image={artifactUrl}
              width={selectedOutcome?.width}
              height={selectedOutcome?.height}
            />
          );
        }
        return null;
      })}
    </div>
  );
};