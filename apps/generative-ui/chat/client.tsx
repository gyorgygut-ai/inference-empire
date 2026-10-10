"use client"
import React from "react"
import { createChatHook } from "@tanstack/ai-react/ui"
import { chatOptions } from "./options"
import { initialChatMessages } from "./options/initialMessages"
import { ChatLayout } from "./components/ChatLayout"
import { ChatMessage } from "./components/ChatMessage"
import { TextPartComponent } from "./parts/components/TextPartComponent"
import { OutcomeOptions } from "./tools/components/OutcomeOptions"
import { ImageUpload } from "./tools/components/ImageUpload"
import { GenerateImageApproval } from "./tools/components/GenerateImageApproval"
import type { PublicOutcome } from "@/outcomes"

export const { useAppChat, useChatContext } = createChatHook({
  options: chatOptions,
  components: {
    layout: ChatLayout,
    message: ChatMessage,
  },
  partsComponents: {
    text: TextPartComponent,
  },
  toolsComponents: {
    presentOutcomeOptions: OutcomeOptions,
    presentImageUpload: ImageUpload,
    runGenerateImage: GenerateImageApproval,
  },
})

export const ChatClient = ({ outcomes }: { outcomes: PublicOutcome[] }) => {
  const chat = useAppChat({
    initialMessages: initialChatMessages(outcomes),
  })

  return <chat.AppChat />
}
