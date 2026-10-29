"use client"
import React from "react"
import { createChatHook } from "@tanstack/ai-react/ui"
import { chatOptions } from "./options"
import { Layout, Message } from "@inference/ui/chat/components"
import { TextPart } from "@inference/ui/chat/parts/components/TextPart"

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

export const ChatClient = () => {
  const chat = useAppChat()
  return <chat.AppChat />
}
