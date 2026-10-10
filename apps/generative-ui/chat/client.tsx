"use client"
import React from "react"
import { createChatHook } from "@tanstack/ai-react/ui"
import { chatOptions } from "./options"
import { initialChatMessages } from "./messages/initial-messages"
import { ChatLayout } from "./components/ChatLayout"
import { ChatMessage } from "./components/ChatMessage"
import { TextPart } from "./parts/components/TextPart"
import { PresentOutcomeOptions } from "./tools/components/PresentOutcomeOptions"
import { PresentImageUpload } from "./tools/components/PresentImageUpload"
import { GenerateImageApproval } from "./tools/components/GenerateImageApproval"
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
    runGenerateImage: GenerateImageApproval,
  },
})

export const ChatClient = ({ outcomes }: { outcomes: PublicOutcome[] }) => {
  const chat = useAppChat({
    initialMessages: initialChatMessages(outcomes),
  })

  return <chat.AppChat />
}
