"use client"

import React from "react"
import { TextPart } from "../../components/TextPart"

export const TextPartComponent = ({ part }: { part: { content: string } }) => (
  <TextPart content={part.content} />
)
