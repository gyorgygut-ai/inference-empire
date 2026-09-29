"use client"

import { MessagePrimitive } from "@assistant-ui/react"
import Image from "next/image"
import { vocabulary } from "@/lib/vocabulary"

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
    <MessagePrimitive.Root className="mb-4">
      <p className="mb-2">{vocabulary.messages.done}</p>
      <figure
        style={{ aspectRatio: `${width} / ${height}` }}
        className="w-full overflow-hidden rounded-lg"
      >
        <Image
          src={image}
          alt="Generated"
          className="h-full w-full object-cover"
          style={{ width, height }}
        />
      </figure>
      <a href={image} download="generated.png" className="mt-2 inline-block text-sm underline">
        Download
      </a>
    </MessagePrimitive.Root>
  )
}
