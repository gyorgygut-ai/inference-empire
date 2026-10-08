"use client"

import React from "react"
import { ChatMessage as UiChatMessage, type ChatMessageProps } from "@tanstack/ai-react/ui"

export const ChatMessage = (props: ChatMessageProps) => (
  <UiChatMessage
    className="flex"
    userClassName="justify-end"
    assistantClassName="justify-start"
    {...props}
  />
)
