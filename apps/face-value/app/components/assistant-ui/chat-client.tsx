"use client"
import { AssistantRuntimeProvider, useLocalRuntime, type ChatModelAdapter } from "@assistant-ui/react"
import Thread from "./thread"
import { ChatProvider } from "./chat-context"

const adapter: ChatModelAdapter = {
  async run({ messages }) {
    const lastUser = [...messages].reverse().find((m) => m.role === "user")
    const text = lastUser?.content.find((c) => c.type === "text") as { text: string } | undefined
    return {
      content: [
        { type: "text", text: `Done: ${text?.text || "outcome"}` },
        { type: "image", image: "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg==" },
      ],
    }
  },
}

export default function ChatClient({
  outcomes,
  serverOnline,
}: {
  outcomes: { id: string; title: string }[]
  serverOnline: boolean
}) {
  const runtime = useLocalRuntime(adapter, {
    initialMessages: serverOnline
      ? []
      : [
          {
            id: "offline",
            role: "system",
            content: [{ type: "text", text: "❌ Server offline" }],
            createdAt: new Date(),
          },
        ],
  })

  return (
    <ChatProvider>
      <AssistantRuntimeProvider runtime={runtime}>
        <Thread outcomes={outcomes} serverOnline={serverOnline} />
      </AssistantRuntimeProvider>
    </ChatProvider>
  )
}