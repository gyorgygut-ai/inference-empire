"use client"
import React from "react"
import { MessageProps } from "@tanstack/ai-react/ui"

export const ChatMessage = <TChatClient,>({ Parts, ...props }: MessageProps<TChatClient>) => (
  <article {...props}>
    <Parts />
  </article>
)
