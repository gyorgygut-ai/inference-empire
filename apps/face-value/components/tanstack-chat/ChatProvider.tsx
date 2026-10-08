"use client";

import React, { useContext, useState, useCallback } from "react";
import { useChat } from "@tanstack/ai-react";
import type { PublicOutcome } from "@/outcomes";
import { vocabulary } from "@/messages/vocabulary";
import { ChatPhase } from "../chat/chat";
import { generateImage } from "@/app/actions/generate";

interface ChatContextValue {
  messages: Array<{
    id: string;
    role: "user" | "assistant";
    parts: Array<{ type: string; content?: string; phase?: ChatPhase }>;
    createdAt: Date;
  }>;
  onSelectOutcome: (id: string) => void;
  referenceFile: File | null;
  setReferenceFile: (file: File | null) => void;
  selectedOutcome: PublicOutcome | null;
  outcomes: PublicOutcome[];
  canGenerate: boolean;
  isLoading: boolean;
  artifactUrl: string | undefined;
  triggerGeneration: () => Promise<void>;
}

const ChatContext = React.createContext<ChatContextValue | null>(null);

export const useChatContext = (): ChatContextValue => {
  const ctx = useContext(ChatContext);
  if (!ctx) {
    throw new Error("useChatContext must be used within ChatProvider");
  }
  return ctx;
};

const offlineFetcher = async (): Promise<Response> => new Response(null, { status: 200 });

interface PhasePart {
  type: "phase";
  phase: ChatPhase;
}

export const ChatProvider = ({
  children,
  initialOutcomes,
}: {
  children: React.ReactNode;
  initialOutcomes: PublicOutcome[];
}) => {
  const { messages, append, isLoading } = useChat({
    fetcher: offlineFetcher,
    initialMessages: [
      {
        id: crypto.randomUUID(),
        role: "assistant",
        parts: [
          { type: "text", content: vocabulary.messages.selectOutcome },
          { type: "phase", phase: ChatPhase.PROMPT_FOR_OUTCOME },
        ],
        createdAt: new Date(),
      },
    ],
  });

  const [selectedOutcome, setSelectedOutcome] = useState<PublicOutcome | null>(null);
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
  const [artifactUrl, setArtifactUrl] = useState<string | undefined>();

  const canGenerate = !!selectedOutcome && !!referenceFile;

  const appendPhaseMessage = useCallback(
    (content: string, phase: ChatPhase) => {
      const alreadyShown = messages.some((m) =>
        m.parts?.some((p) => p.type === "phase" && (p as PhasePart).phase === phase)
      );
      if (alreadyShown) return;
      append({
        id: crypto.randomUUID(),
        role: "assistant",
        parts: [
          { type: "text", content },
          { type: "phase", phase },
        ],
        createdAt: new Date(),
      });
    },
    [append, messages]
  );

  // Phase transitions in event handlers — NO useEffect
  const onSelectOutcome = useCallback(
    (id: string) => {
      const outcome = initialOutcomes.find((o) => o.id === id) ?? null;
      setSelectedOutcome(outcome);
      if (outcome) {
        // FIX: Append BOTH prompts after outcome selection
        // 1. PROMPT_FOR_REFERENCE — "Upload your photo..."
        // 2. REQUEST_INFERENCE — "Let's do this!"
        appendPhaseMessage(vocabulary.messages.uploadReference, ChatPhase.PROMPT_FOR_REFERENCE);
        appendPhaseMessage(vocabulary.messages.requestInference, ChatPhase.REQUEST_INFERENCE);
      }
    },
    [initialOutcomes, appendPhaseMessage]
  );

  const onFileSelect = useCallback(
    (file: File | null) => {
      setReferenceFile(file);
      if (file && selectedOutcome) {
        appendPhaseMessage(vocabulary.messages.uploadReference, ChatPhase.PROMPT_FOR_REFERENCE);
        appendPhaseMessage(vocabulary.messages.requestInference, ChatPhase.REQUEST_INFERENCE);
      }
    },
    [selectedOutcome, appendPhaseMessage]
  );

  const triggerGeneration = useCallback(async () => {
    if (!canGenerate || !selectedOutcome || !referenceFile) {
      return;
    }

    appendPhaseMessage(vocabulary.messages.busy, ChatPhase.INFERENCE_BUSY);

    try {
      const response = await generateImage(selectedOutcome.id, referenceFile);
      if (response.status === "rejected") {
        appendPhaseMessage(vocabulary.messages.rejected, ChatPhase.INFERENCE_REJECTED);
      } else {
        appendPhaseMessage(vocabulary.messages.fulfilled, ChatPhase.INFERENCE_FULFILLED);
        setArtifactUrl(response.presignedUrl);
      }
    } catch {
      appendPhaseMessage(vocabulary.messages.rejected, ChatPhase.INFERENCE_REJECTED);
    }
  }, [canGenerate, selectedOutcome, referenceFile, appendPhaseMessage]);

  return (
    <ChatContext.Provider
      value={{
        messages,
        onSelectOutcome,
        referenceFile,
        setReferenceFile: onFileSelect,
        selectedOutcome,
        outcomes: initialOutcomes,
        canGenerate,
        isLoading,
        artifactUrl,
        triggerGeneration,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
};