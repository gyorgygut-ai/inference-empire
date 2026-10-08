"use client";

import { createChatHook } from "@tanstack/ai-react/ui";
import { generateImageTool } from "./tools/generate-image-tool";
import { GenerateImageTool } from "./tools/GenerateImageTool";
import { ChatLayout } from "./ChatLayout";
import { ChatMessage } from "./ChatMessage";
import { TextPart } from "./TextPart";

const chatHook = createChatHook({
  options: {
    tools: [generateImageTool],
  },
  components: {
    layout: ChatLayout,
    message: ChatMessage,
  },
  partsComponents: {
    text: TextPart,
    image: ({ part }: any) => (
      <img
        src={part.image}
        alt="Uploaded"
        className="max-w-full max-h-64 rounded-lg object-cover"
      />
    ),
    fallback: () => null,
  },
  toolsComponents: {
    generateImage: GenerateImageTool,
  },
});

export const { useAppChat, useChatContext } = chatHook;
