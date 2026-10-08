"use client"

import React from "react"
import { createChatHook } from "@tanstack/ai-react/ui"
import { ChatLayout } from "./ChatLayout"
import { ChatMessage } from "./ChatMessage"
import { TextPart } from "./TextPart"
import { vocabulary } from "@/messages"
import type { PublicOutcome } from "@/outcomes/outcomes"

export const { useAppChat, useChatContext } = createChatHook({
  options: {
    fetcher: async () => {
      throw new Error("Append-only chat: no LLM transport")
    },
  },
  components: {
    layout: ChatLayout,
    message: ChatMessage,
  },
  partsComponents: {
    text: TextPart,
  },
})

export const ChatClient = ({ outcomes }: { outcomes: PublicOutcome[] }) => {
  const chat = useAppChat({
    initialMessages: [
      {
        id: "select-outcome",
        role: "assistant",
        metadata: { outcomes },
        parts: [{ type: "text", content: vocabulary.messages.selectOutcome }],
      },
    ],
  })

  return <chat.AppChat />
}
