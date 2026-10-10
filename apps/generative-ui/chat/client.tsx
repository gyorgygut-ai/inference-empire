"use client"
import React from "react"
import { createChatHook } from "@tanstack/ai-react/ui"
import { chatOptions } from "./options"
import { initialChatMessages } from "./options/initialMessages"
import { ChatLayout } from "./components/ChatLayout"
import { ChatMessage } from "./components/ChatMessage"
import { TextPartComponent } from "./parts/components/TextPartComponent"
import { ShowOutcomeOptions } from "./tools/components/ShowOutcomeOptions"
import type { PublicOutcome } from "@/outcomes/outcomes"

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
    showOutcomeOptions: ShowOutcomeOptions,
  },
})

export const ChatClient = ({ outcomes: _outcomes }: { outcomes: PublicOutcome[] }) => {
  const chat = useAppChat({
    initialMessages: initialChatMessages(),
  })

  return <chat.AppChat />
}
