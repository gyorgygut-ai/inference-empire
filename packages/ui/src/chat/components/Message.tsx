"use client"
import React from "react"
import { MessageProps } from "@tanstack/ai-react/ui"

export const Message = <TChatClient,>({ Parts, message }: MessageProps<TChatClient>) => {
  if (!message.parts || message.parts.length === 0) {
    return null
  }

  const isUser = message.role === "user"

  return (
    <article className={`flex flex-col gap-2 ${isUser ? "items-end" : "items-start"}`}>
      <div
        className={
          isUser
            ? "max-w-full rounded-xl bg-primary px-4 py-3 text-primary-foreground"
            : "max-w-full text-secondary-foreground"
        }
      >
        <Parts />
      </div>
    </article>
  )
}
