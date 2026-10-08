"use client";

import { createChatHook } from "@tanstack/ai-react/ui";
import { generateImageTool } from "./tools/generate-image-tool";
import { GenerateImageTool } from "./tools/GenerateImageTool";
import { ChatLayout } from "./ChatLayout";
import { ChatMessage } from "./ChatMessage";

export const { useAppChat, useChatContext } = createChatHook({
  options: {
    tools: [generateImageTool],
  },
  components: {
    layout: ChatLayout,
    message: ChatMessage,
  },
  toolsComponents: {
    generateImage: GenerateImageTool,
  },
});
