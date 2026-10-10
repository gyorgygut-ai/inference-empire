import type { ImagePart } from "@tanstack/ai"

export function imagePart(base64: string, mimeType: string): ImagePart {
  return { type: "image", source: { type: "data", value: base64, mimeType } }
}
