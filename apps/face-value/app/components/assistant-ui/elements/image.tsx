"use client"
import type { ImageMessagePart, ImageMessagePartComponent } from "@assistant-ui/react"
import { useState, useCallback, useRef, useEffect, memo } from "react"

const downloadImagePart = (part: Pick<ImageMessagePart, "image" | "filename">): void => {
  if (typeof document === "undefined") return
  const filename = part.filename ?? "image.png"
  const isDataUri = /^data:/i.test(part.image)
  let href: string | null = null
  if (isDataUri) {
    try {
      const commaIndex = part.image.indexOf(",")
      const base64 = commaIndex > 0 ? part.image.slice(commaIndex + 1) : ""
      const byteCharacters = atob(base64)
      const byteNumbers = new Array(byteCharacters.length)
      for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i)
      }
      const byteArray = new Uint8Array(byteNumbers)
      const blob = new Blob([byteArray], { type: "image/png" })
      href = URL.createObjectURL(blob)
    } catch {
      href = part.image
    }
  } else {
    href = part.image
  }
  if (!href) return
  const a = document.createElement("a")
  a.href = href!
  a.download = filename
  a.rel = "noopener"
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  if (href!.startsWith("blob:")) {
    setTimeout(() => URL.revokeObjectURL(href!), 40_000)
  }
}

const downloadIcon = (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
    <polyline points="7 10 12 15 17 10" />
    <line x1="12" y1="15" x2="12" y2="3" />
  </svg>
)

export function ImageActions({ part }: { part: ImageMessagePart }) {
  const { image, filename } = part
  return (
    <div className="flex items-center gap-1 p-1">
      <button
        type="button"
        onClick={() => downloadImagePart(part)}
        className="hover:bg-gray-100 inline-flex size-7 items-center justify-center rounded text-gray-500"
        aria-label="Download image"
      >
        {downloadIcon}
      </button>
    </div>
  )
}

const ImageRoot = memo(function ImageRoot({
  className,
  children,
}: {
  className?: string
  children: React.ReactNode
}) {
  return (
    <div className={`aui-image-root relative overflow-hidden rounded-lg border ${className ?? ""}`}>
      {children}
    </div>
  )
})

const ImageImpl: ImageMessagePartComponent = (props) => {
  const { image, filename, status } = props

  if (status?.type === "running") {
    return (
      <ImageRoot className="bg-gray-100">
        <div className="flex min-h-32 items-center justify-center p-4">
          <div className="size-8 animate-spin rounded-full border-2 border-gray-300 border-t-gray-600" />
          <span className="sr-only">Generating image…</span>
        </div>
      </ImageRoot>
    )
  }

  return (
    <ImageRoot>
      <img
        src={image}
        alt={filename || "Generated image"}
        className="block h-auto w-full object-contain"
      />
      <ImageActions part={props} />
    </ImageRoot>
  )
}

export const Image = memo(ImageImpl) as unknown as ImageMessagePartComponent & {
  Actions: typeof ImageActions
}

Image.displayName = "Image"
Image.Actions = ImageActions
