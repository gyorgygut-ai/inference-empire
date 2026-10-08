"use client"
import React from "react"
import {
  ChatMessage as UiChatMessage,
  type ChatMessageProps,
} from "@tanstack/ai-react/ui"
import { vocabulary } from "@/messages"
import { FileUpload } from "./FileUpload"

export const ChatMessage = (props: ChatMessageProps) => {
  const message = props.message
  
  // Check if this message should show the file upload UI
  const showFileUpload = 
    message.role === 'assistant' && 
    message.parts.some(p => p.type === 'text' && p.content === vocabulary.messages.uploadReference)

  return (
    <div id={message.id}>
      <UiChatMessage
        className="mb-4 animate-in fade-in-50 slide-in-from-bottom-2 duration-300 bg-surface rounded-xl p-4 text-sm flex"
        userClassName="justify-end"
        assistantClassName="justify-start"
        {...props}
      />
      {showFileUpload && <FileUpload />}
    </div>
  )
}