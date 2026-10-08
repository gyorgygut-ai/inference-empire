"use client";

import { createChatHook } from "@tanstack/ai-react/ui";
import { ChatLayout } from "./ChatLayout";
import { ChatMessage } from "./ChatMessage";
import { TextPart } from "./TextPart";
import { vocabulary } from "@/messages";

export const { useAppChat, useChatContext } = createChatHook({
  options: {
    fetcher: async () => {
      throw new Error("Append-only chat: no LLM transport");
    },
    initialMessages: [
      {
        id: "select-outcome",
        role: "assistant",
        parts: [{ type: "text", content: vocabulary.messages.selectOutcome }],
      },
    ],
  },
  components: {
    layout: ChatLayout,
    message: ChatMessage,
  },
  partsComponents: {
    text: TextPart,
  },
});
