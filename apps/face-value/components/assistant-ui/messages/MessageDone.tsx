"use client"

import { MessagePrimitive } from "@assistant-ui/react"
import { vocabulary } from "@/messages/vocabulary"

export function MessageDone({
  image,
  width,
  height,
}: {
  image: string
  width: number
  height: number
}) {
  return (
    <MessagePrimitive.Root className="mb-4 animate-in fade-in-50 slide-in-from-bottom-2 duration-300 bg-surface rounded-xl p-4">
      <p className="mb-2">{vocabulary.messages.done}</p>
      <figure
        style={{ aspectRatio: `${width} / ${height}` }}
        className="w-full overflow-hidden rounded-lg"
      >
        <img
          src={image}
          alt="Generated"
          className="h-full w-full object-cover"
        />
      </figure>
      <a href={image} download="generated.png" className="mt-2 inline-block text-sm underline">
        Download
      </a>
    </MessagePrimitive.Root>
  )
}