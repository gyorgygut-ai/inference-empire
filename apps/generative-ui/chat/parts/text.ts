import type { TextPart } from "@tanstack/ai"

export function textPart(content: string): TextPart {
  return { type: "text", content }
}
