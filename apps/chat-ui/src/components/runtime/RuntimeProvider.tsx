"use client"

import { createContext, useContext, useState, useEffect, useRef } from "react"
import { AssistantRuntimeProvider, useAui } from "@assistant-ui/react"
import { useLocalRuntime } from "@assistant-ui/react"
import { buildInputs, type ModelGroup } from "@/lib/chat/directHandlers"
import { chatTools } from "@/lib/chat/tools"

interface ChatContextValue {
  group: ModelGroup
  setGroup: (g: ModelGroup) => void
  boxes: Record<string, unknown>
  setBoxes: (b: Record<string, unknown>) => void
  imageBase64: string | null
  setImageBase64: (v: string | null) => void
}

const ChatContext = createContext<ChatContextValue | null>(null)

export function useChatContext() {
  const ctx = useContext(ChatContext)
  if (!ctx) throw new Error("useChatContext outside provider")
  return ctx
}

export function RuntimeProvider({ children }: { children: React.ReactNode }) {
  const [group, setGroup] = useState<ModelGroup>("flux")
  const [boxes, setBoxes] = useState<Record<string, unknown>>({})
  const [imageBase64, setImageBase64] = useState<string | null>(null)

  void chatTools

  const ctxRef = useRef({ group, boxes, imageBase64 })
  useEffect(() => { ctxRef.current = { group, boxes, imageBase64 } }, [group, boxes, imageBase64])

  const aui = useAui()
  // modelContext sync is best-effort; API may vary by version
  useEffect(() => {
    try {
      // @ts-ignore
      aui.modelContext?.set?.({ group, boxes, imageBase64 })
    } catch {}
  }, [aui, group, boxes, imageBase64])

  const runtime = useLocalRuntime({
    async run({ messages, abortSignal }) {
      const last = messages[messages.length - 1] as unknown as { content: unknown }
      const content = last?.content as unknown
      let prompt = ""
      if (typeof content === "string") prompt = content
      else if (Array.isArray(content)) prompt = (content as { text?: string }[]).map((p) => p.text ?? "").join("")
      else prompt = String(content ?? "")

      const { group: g, boxes: b, imageBase64: ib } = ctxRef.current
      const { model, inputs } = buildInputs(g, String(prompt), b, ib ?? undefined)

      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ model, inputs }),
        signal: abortSignal,
      })
      const data = await res.json()

      if (data.classification || data.subjects || data.description) {
        return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] }
      }

      if (data.presigned_url) {
        const isVideo = model.startsWith("minimax_h3")
        const url = data.presigned_url as string
        if (isVideo) {
          return { content: [{ type: "file", data: url, mimeType: "video/mp4" }] }
        }
        return { content: [{ type: "image", image: url }] }
      }

      return { content: [{ type: "text", text: JSON.stringify(data, null, 2) }] }
    },
  })

  return (
    <ChatContext.Provider value={{ group, setGroup, boxes, setBoxes, imageBase64, setImageBase64 }}>
      <AssistantRuntimeProvider runtime={runtime}>{children}</AssistantRuntimeProvider>
    </ChatContext.Provider>
  )
}
