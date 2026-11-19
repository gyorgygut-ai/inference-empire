import React from "react"
import type { ImagePart as TanStackImagePart } from "@tanstack/ai"

export const ImagePart = ({
  alt = "Image",
  part,
}: {
  alt?: string
  part: TanStackImagePart
}) => {
  const { source } = part
  const src =
    source.type === "data"
      ? `data:${source.mimeType};base64,${source.value}`
      : source.type === "url"
        ? source.value
        : undefined

  if (!src) {
    return null
  }

  return <img alt={alt} className="max-w-48 rounded-xl" src={src} />
}
