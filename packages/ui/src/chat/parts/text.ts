import type { TextPart } from "@tanstack/ai-client"

export function textPart(content: string): TextPart {
  return { type: "text", content }
}