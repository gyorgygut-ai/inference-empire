"use client";

import { createContext, useContext, useState, type ReactNode } from "react";
import type { Outcome } from "@/outcomes";

interface ChatContextValue {
  selectedOutcomeId: string | null;
  setSelectedOutcomeId: (id: string | null) => void;
  lastImageData: string | null;
  setLastImageData: (data: string | null) => void;
  hasAttachment: boolean;
  setHasAttachment: (has: boolean) => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

export function ChatProvider({ children }: { children: ReactNode }) {
  const [selectedOutcomeId, setSelectedOutcomeId] = useState<string | null>(null);
  const [lastImageData, setLastImageData] = useState<string | null>(null);
  const [hasAttachment, setHasAttachment] = useState(false);

  return (
    <ChatContext.Provider
      value={{
        selectedOutcomeId,
        setSelectedOutcomeId,
        lastImageData,
        setLastImageData,
        hasAttachment,
        setHasAttachment,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
}

export function useChat() {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error("useChat must be used within a ChatProvider");
  }
  return context;
}