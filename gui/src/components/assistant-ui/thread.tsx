"use client"

import {
  ThreadPrimitive,
  ComposerPrimitive,
  MessagePrimitive,
  AttachmentPrimitive,
} from "@assistant-ui/react"
import type { FC } from "react"

export const Thread: FC = () => {
  return (
    <ThreadPrimitive.Root className="flex h-full min-h-0 flex-col bg-background">
      <ThreadPrimitive.Viewport className="flex flex-1 flex-col gap-4 overflow-y-auto p-4">
        <ThreadPrimitive.Empty>
          <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
            Start a conversation
          </div>
        </ThreadPrimitive.Empty>
        <ThreadPrimitive.Messages
          components={{
            UserMessage: UserMessage,
            AssistantMessage: AssistantMessage,
          }}
        />
      </ThreadPrimitive.Viewport>
      <div className="shrink-0 border-t border-border p-3">
        <Composer />
      </div>
    </ThreadPrimitive.Root>
  )
}

const UserMessage: FC = () => {
  return (
    <MessagePrimitive.Root className="ml-auto max-w-[80%] rounded-lg bg-primary px-3 py-2 text-sm text-primary-foreground">
      <MessagePrimitive.Content />
    </MessagePrimitive.Root>
  )
}

const AssistantMessage: FC = () => {
  return (
    <MessagePrimitive.Root className="flex flex-col gap-2">
      <MessagePrimitive.Content />
      <MessagePrimitive.Parts
        components={{
          Text: (props: { text: string }) => <span className="text-sm text-foreground whitespace-pre-wrap">{props.text}</span>,
          Image: (props: { image: string }) => (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={props.image} alt="generated" className="max-h-64 rounded border" />
          ),
          File: (props: { filename?: string; src?: string; file?: string; data?: string }) => {
            const src = props.src ?? props.file ?? props.data
            const isVideo = props.filename?.match(/\.(mp4|webm|mov)$/i) || String(src ?? "").match(/\.(mp4|webm|mov)$/i)
            if (isVideo && src) return <video src={src} controls className="max-h-64 rounded border" />
            if (src) return <a href={src} target="_blank" rel="noopener noreferrer" className="text-sm text-primary underline">{props.filename ?? src}</a>
            return <span className="text-sm text-muted-foreground">{props.filename ?? "file"}</span>
          },
        }}
      />
    </MessagePrimitive.Root>
  )
}

const Composer: FC = () => {
  return (
    <ComposerPrimitive.Root className="flex items-end gap-2 rounded-lg border border-input bg-background p-2">
      <AttachmentPrimitive.Root>
        {/* Attachment UI is provided by assistant-ui primitives; custom trigger omitted for compatibility */}
      </AttachmentPrimitive.Root>
      <ComposerPrimitive.Input
        autoFocus
        placeholder="Type a message..."
        className="min-h-10 flex-1 resize-none bg-transparent text-sm outline-none placeholder:text-muted-foreground"
      />
      <ComposerPrimitive.Send className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
        Send
      </ComposerPrimitive.Send>
    </ComposerPrimitive.Root>
  )
}
