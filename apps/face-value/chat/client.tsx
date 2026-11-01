"use client"
import React, { useId } from "react"
import { createChatHook } from "@tanstack/ai-react/ui"
import { chatOptions } from "./options"
import { initialMessage } from "./messages/initialMessage"
import { Layout, Message } from "@inference/ui/chat/components"
import { TextPart } from "@inference/ui/chat/parts/components/TextPart"
import type { PublicOutcome } from "@/outcomes"
import { PresentOutcomeOptions } from "./tools/presentOutcomeOptions"
import { PresentImageUpload } from "./tools/presentImageUpload"
import { GenerateImageTool } from "./tools/runGenerateImage"

export const { useAppChat, useChatContext } = createChatHook({
  options: chatOptions,
  components: {
    layout: Layout,
    message: Message,
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
    threadId: useId(),
    initialMessages: [initialMessage(outcomes)],
  })

  return <chat.AppChat />
}
