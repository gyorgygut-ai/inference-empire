"use client"
import React from "react"
import { createChatHook } from "@tanstack/ai-react/ui"
import { chatOptions } from "./options"
import { initialMessage } from "./messages/initialMessage"
import { Layout, Message } from "@inference/ui/chat/components"
import { TextPart } from "@inference/ui/chat/parts/components/TextPart"
import type { PublicOutcome } from "@/outcomes"

export const { useAppChat, useChatContext } = createChatHook({
  options: chatOptions,
  components: {
    layout: Layout,
    message: Message,
  },
  partsComponents: {
    text: TextPart,
  },
})

export const ChatClient = ({ outcomes }: { outcomes: PublicOutcome[] }) => {
  const chat = useAppChat({
    initialMessages: [initialMessage(outcomes)],
  })

  return <chat.AppChat />
}