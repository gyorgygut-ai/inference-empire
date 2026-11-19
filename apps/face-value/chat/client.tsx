"use client"
import React, { useId } from "react"
import { createChatHook } from "@tanstack/ai-react/ui"
import { chatOptions } from "./options"
import { initialMessage } from "./messages/initialMessage"
import { Message } from "@inference/ui/chat/components"
import { ImagePart } from "@inference/ui/chat/parts/components/ImagePart"
import { TextPart } from "@inference/ui/chat/parts/components/TextPart"
import type { PublicOutcome } from "@/outcomes"
import { PresentOutcomeOptions } from "./tools/presentOutcomeOptions"
import { PresentImageUpload } from "./tools/presentImageUpload"
import { GenerateImageTool } from "./tools/runGenerateImage"
import { ChatLayout } from "./shell/ChatLayout"
import { chatContext, interruptContext, partContext } from "./contexts"

export const { useAppChat, useChatContext } = createChatHook({
  options: chatOptions,
  context: { chatContext, interruptContext, partContext },
  components: {
    layout: ChatLayout,
    message: Message,
  },
  partsComponents: {
    text: TextPart,
    image: ImagePart,
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
