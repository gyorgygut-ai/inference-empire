"use client"
import React from "react"
import { MessageProps } from "@tanstack/ai-react/ui"

export const Message = <TChatClient,>({ Parts, message }: MessageProps<TChatClient>) => {
  if (!message.parts || message.parts.length === 0) return null
  return <article className="flex flex-col gap-2"><Parts /></article>
}