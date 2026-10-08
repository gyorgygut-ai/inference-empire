"use client"

import React from "react"
import { ChatMessage as UiChatMessage, type ChatMessageProps } from "@tanstack/ai-react/ui"

export const ChatMessage = (props: ChatMessageProps) => (
  <UiChatMessage
    className="mb-4 animate-in fade-in-50 slide-in-from-bottom-2 duration-300 bg-surface rounded-xl p-4 text-sm flex"
    userClassName="justify-end"
    assistantClassName="justify-start"
    {...props}
  />
)
