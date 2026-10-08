"use client"

import React from "react"
import { TextPart as TanStackTextPart } from "@tanstack/ai-react/ui"

export const TextPart = ({ part }: { part: { content: string } }) => (
  <TanStackTextPart
    content={part.content}
    className="whitespace-pre-wrap leading-relaxed"
    userClassName="text-primary-foreground"
    assistantClassName="text-secondary-foreground"
  />
)
