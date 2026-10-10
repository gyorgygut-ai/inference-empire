"use client"

import {
  TextPart as OriginalTextPart,
} from "@tanstack/ai-react/ui"

export const TextPart = ({ part }: { part: { content: string } }) => (
  <OriginalTextPart
    content={part.content}
    userClassName="text-primary-foreground"
    assistantClassName="text-secondary-foreground"
    className="mb-4 animate-in fade-in-50 slide-in-from-bottom-2 duration-300 bg-surface rounded-xl p-4 text-sm flex"
  />
)
