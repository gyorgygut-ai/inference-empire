"use client"
import React from "react"
import { createChatHook } from "@tanstack/ai-react/ui"
import { ChatLayout } from "./ChatLayout"
import { ChatMessage } from "./ChatMessage"
import { TextPart } from "./TextPart"
import { OutcomeSelector } from "./OutcomeSelector"
import { FileUploadPart } from "./FileUploadPart"
import { SubmitButtonPart } from "./SubmitButtonPart"
import { vocabulary } from "@/messages"
import type { PublicOutcome } from "@/outcomes/outcomes"

export const { useAppChat, useChatContext } = createChatHook({
  options: {
    fetcher: async () => { throw new Error("Append-only chat: no LLM transport") },
  },
  components: {
    layout: ChatLayout,
    message: ChatMessage,
  },
  partsComponents: {
    text: TextPart,
    fallback: ({ part }) => {
      if (part.type === "activity") {
        const { append } = useChatContext()
        
        if (part.activityType === "outcomeSelector") {
          const outcomes = (part.content as { outcomes: PublicOutcome[] }).outcomes || []
          return <OutcomeSelector outcomes={outcomes} append={append} />
        }
        if (part.activityType === "fileUpload") {
          return <FileUploadPart append={append} />
        }
        if (part.activityType === "submitButton") {
          return <SubmitButtonPart append={append} />
        }
      }
      return null
    },
  },
})

export const ChatClient = ({ outcomes }: { outcomes: PublicOutcome[] }) => {
  const chat = useAppChat({
    initialMessages: [
      {
        id: "select-outcome",
        role: "assistant",
        metadata: { outcomes },
        parts: [
          { type: "text", content: vocabulary.messages.selectOutcome },
          { 
            type: "activity", 
            activityType: "outcomeSelector", 
            content: { outcomes } 
          },
        ],
      },
    ],
  })

  return <chat.AppChat />
}