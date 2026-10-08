"use client";

import React, { useContext, useState, useCallback, useEffect } from "react";
import { useChat } from "@tanstack/ai-react";
import type { PublicOutcome } from "@/outcomes";
import { vocabulary } from "@/messages/vocabulary";
import { ChatPhase } from "../assistant-ui/chat";
import { generateImage } from "@/app/actions/generate";

interface ChatContextValue {
  messages: Array<any>;
  appendMessage: (content: string, phase?: ChatPhase) => void;
  onSelectOutcome: (id: string) => void;
  referenceFile: File | null;
  setReferenceFile: (file: File | null) => void;
  selectedOutcome: PublicOutcome | null;
  outcomes: PublicOutcome[];
  canGenerate: boolean;
  isLoading: boolean;
  artifactUrl: string | undefined;
  getMessagePhase: (id: string) => ChatPhase | undefined;
  triggerGeneration: () => Promise<void>;
}

const ChatContext = React.createContext<ChatContextValue | null>(null);

export const useChatContext = () => {
  const ctx = useContext(ChatContext);
  if (!ctx) {
    throw new Error("useChatContext must be used within ChatProvider");
  }
  return ctx;
};

// Minimal fetcher for offline use - just returns empty response
const offlineFetcher = async () => new Response(null, { status: 200 });

export const ChatProvider = ({
  children,
  initialOutcomes,
}: {
  children: React.ReactNode;
  initialOutcomes: PublicOutcome[];
}) => {
  const { messages, append } = useChat({ fetcher: offlineFetcher });
  const [selectedOutcome, setSelectedOutcome] = useState<PublicOutcome | null>(null);
  const [referenceFile, setReferenceFile] = useState<File | null>(null);
  const [generationState, setGenerationState] = useState<
    "idle" | "busy" | "rejected" | "fulfilled"
  >("idle");
  const [artifactUrl, setArtifactUrl] = useState<string | undefined>();
  const [messagePhases, setMessagePhases] = useState<Map<string, ChatPhase>>(
    new Map()
  );

  const canGenerate = !!selectedOutcome && !!referenceFile;

  const appendMessage = useCallback(
    (content: string, phase?: ChatPhase) => {
      const id = crypto.randomUUID();
      append({
        id,
        role: "assistant",
        parts: [{ type: "text", content }],
        createdAt: new Date(),
      });
      if (phase) {
        setMessagePhases((prev) => new Map(prev.set(id, phase)));
      }
    },
    [append]
  );

  const getMessagePhase = useCallback((id: string) => messagePhases.get(id), [
    messagePhases,
  ]);

  const onSelectOutcome = useCallback(
    (id: string) =>
      setSelectedOutcome(initialOutcomes.find((o) => o.id === id) ?? null),
    [initialOutcomes]
  );

  const triggerGeneration = useCallback(async () => {
    if (!canGenerate || !selectedOutcome || !referenceFile) {
      return;
    }

    setGenerationState("busy");

    // Append busy message immediately (3-dot animation, no text)
    appendMessage(vocabulary.messages.busy, ChatPhase.INFERENCE_BUSY);

    // Schedule busyForAWhile after 35s per spec
    const busyForAWhileTimer = setTimeout(() => {
      appendMessage(
        vocabulary.messages.busyForAWhile,
        ChatPhase.INFERENCE_BUSY
      );
    }, 35000);

    try {
      const response = await generateImage(selectedOutcome.id, referenceFile);
      clearTimeout(busyForAWhileTimer);

      if (response.status === "rejected") {
        appendMessage(
          vocabulary.messages.rejected,
          ChatPhase.INFERENCE_REJECTED
        );
        setGenerationState("rejected");
      } else {
        appendMessage(
          vocabulary.messages.fulfilled,
          ChatPhase.INFERENCE_FULFILLED
        );
        setArtifactUrl(response.presignedUrl);
        setGenerationState("fulfilled");
      }
    } catch {
      clearTimeout(busyForAWhileTimer);
      appendMessage(
        vocabulary.messages.rejected,
        ChatPhase.INFERENCE_REJECTED
      );
      setGenerationState("rejected");
    }
  }, [canGenerate, selectedOutcome, referenceFile, appendMessage]);

  // Initial prompt effect - seed the thread with outcome prompt
  useEffect(() => {
    if (messages.length === 0) {
      appendMessage(
        vocabulary.messages.selectOutcome,
        ChatPhase.PROMPT_FOR_OUTCOME
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages.length, appendMessage]);

  // Reference prompt effect - triggers when user selects outcome and uploads image.
  useEffect(() => {
    if (selectedOutcome && referenceFile) {
      const hasReferencePrompt = Array.from(messagePhases.values()).includes(
        ChatPhase.PROMPT_FOR_REFERENCE
      );
      if (!hasReferencePrompt) {
        appendMessage(
          vocabulary.messages.uploadReference,
          ChatPhase.PROMPT_FOR_REFERENCE
        );
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedOutcome, referenceFile, messagePhases, appendMessage]);

  return (
    <ChatContext.Provider
      value={{
        messages,
        appendMessage,
        onSelectOutcome,
        referenceFile,
        setReferenceFile,
        selectedOutcome,
        outcomes: initialOutcomes,
        canGenerate,
        isLoading: generationState === "busy",
        artifactUrl,
        getMessagePhase,
        triggerGeneration,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
};