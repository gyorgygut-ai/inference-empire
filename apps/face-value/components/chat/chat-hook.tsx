"use client";

import { createChatHook } from "@tanstack/ai-react/ui";
import { clientTools } from "@tanstack/ai-react";
import { generateImageTool } from "./tools/generate-image-tool";
import { GenerateImageTool } from "./tools/GenerateImageTool";
import { ChatLayout } from "./ChatLayout";
import { ChatMessage } from "./ChatMessage";
import { vocabulary } from "@/messages";

export const { useAppChat, useChatContext } = createChatHook({
  options: {
    tools: clientTools(generateImageTool),
    fetcher: async () => new Response(),
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
  partsComponents: {},
  toolsComponents: {
    generateImage: GenerateImageTool,
  },
});
