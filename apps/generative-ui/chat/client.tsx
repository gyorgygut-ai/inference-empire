"use client"
import React from "react"
import { createChatHook } from "@tanstack/ai-react/ui"
import { chatOptions } from "./options"
import { initialMessage } from "./messages/initialMessage"
import { ChatLayout } from "./components/ChatLayout"
import { ChatMessage } from "./components/ChatMessage"
import { TextPart } from "./parts/components/TextPart"
import { PresentOutcomeOptions } from "./tools/components/PresentOutcomeOptions"
import { PresentImageUpload } from "./tools/components/PresentImageUpload"
import { GenerateImageTool } from "./tools/components/GenerateImageTool"
import type { PublicOutcome } from "@/outcomes"

export const { useAppChat, useChatContext } = createChatHook({
  options: chatOptions,
  components: {
    layout: ChatLayout,
    message: ChatMessage,
  },
  partsComponents: {
    text: TextPart,
  },
  toolsComponents: {
    presentOutcomeOptions: PresentOutcomeOptions,
    presentImageUpload: PresentImageUpload,
    runGenerateImage: GenerateImageTool,
  },
})

export const ChatClient = ({ outcomes }: { outcomes: PublicOutcome[] }) => {
  const chat = useAppChat({
    initialMessages: [initialMessage(outcomes)],
  })

  return <chat.AppChat />
}
