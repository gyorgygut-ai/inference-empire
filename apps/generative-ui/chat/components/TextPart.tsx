"use client"

import React from "react"
import {
  TextPart as OriginalTextPart,
  type TextPartProps,
} from "@tanstack/ai-react/ui"

export const TextPart = ({ content }: TextPartProps) => (
  <OriginalTextPart
    content={content}
    userClassName="text-primary-foreground"
    assistantClassName="text-secondary-foreground"
    className="mb-4 animate-in fade-in-50 slide-in-from-bottom-2 duration-300 bg-surface rounded-xl p-4 text-sm flex"
  />
)
