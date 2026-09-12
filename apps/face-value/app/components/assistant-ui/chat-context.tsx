"use client"
import { createContext, useContext, useState } from "react"
import type { ReactNode } from "react"

type ChatContextType = {
  selectedOutcomeId: string | null
  setSelectedOutcomeId: (id: string | null) => void
  hasAttachment: boolean
  setHasAttachment: (has: boolean) => void
}

const ChatContext = createContext<ChatContextType | null>(null)

export function ChatProvider({ children }: { children: ReactNode }) {
  const [selectedOutcomeId, setSelectedOutcomeId] = useState<string | null>(null)
  const [hasAttachment, setHasAttachment] = useState(false)
  return (
    <ChatContext.Provider value={{ selectedOutcomeId, setSelectedOutcomeId, hasAttachment, setHasAttachment }}>
      {children}
    </ChatContext.Provider>
  )
}

export function useChat() {
  const ctx = useContext(ChatContext)
  if (!ctx) throw new Error("useChat must be used within a ChatProvider")
  return ctx
}