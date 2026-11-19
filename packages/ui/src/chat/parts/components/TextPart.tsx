"use client"

import React from "react"
import {
  TextPart as OriginalTextPart,
} from "@tanstack/ai-react/ui"

export const TextPart = ({ part }: { part: { content: string } }) => (
  <OriginalTextPart content={part.content} className="whitespace-pre-wrap leading-relaxed" />
)
