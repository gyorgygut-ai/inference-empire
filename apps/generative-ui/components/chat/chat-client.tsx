"use client";
import React from "react";
import { createChatOptions } from "@tanstack/ai";
import { createChatHook } from "@tanstack/ai-react/ui";
import { TextPart } from "./ui/TextPart";
import { ChatLayout } from "./ui/ChatLayout";
import { ChatMessage } from "./ui/ChatMessage";
// import { OutcomeSelector } from "./OutcomeSelector"
// import { FileUploadPart } from "./FileUploadPart"
// import { SubmitButtonPart } from "./SubmitButtonPart"
import { assistantMessagePromptForOutcome } from "./messages";
import type { PublicOutcome } from "@/outcomes/outcomes";

export const { useAppChat, useChatContext } = createChatHook({
  options: {
    fetcher: async () => {
      throw new Error("Append-only chat: no LLM transport");
    },
  },
  components: {
    layout: ChatLayout,
    message: ChatMessage,
  },
  partsComponents: {
    text: ({ part }) => <TextPart {...part} />,
  },
  toolsComponents: {
    showOutcomeOptions: () => <div>sdfdf</div>,
  },
});

export const ChatClient = ({
  outcomes: _outcomes,
}: {
  outcomes: PublicOutcome[];
}) => {
  const chat = useAppChat({
    initialMessages: [assistantMessagePromptForOutcome()],
  });

  return <chat.AppChat />;
};
