"use client"
import React from "react"
import { MessageProps } from "@tanstack/ai-react/ui"

export const Message = <TChatClient,>({ Parts, ...props }: MessageProps<TChatClient>) => (
  <article {...props} className="flex flex-col gap-2">
    <Parts />
  </article>
)