"use client";

import { useCallback, useEffect, useState } from "react";
import { useAui } from "@assistant-ui/react";
import { useChat } from "./chat-context";
import { vocabulary } from "@/app/vocabulary";
import type { Outcome } from "@/outcomes";

type FlowPhase =
  | { phase: "OUTCOME_SELECTION" }
  | { phase: "IMAGE_UPLOAD"; outcomeId: string }
  | { phase: "GENERATING"; outcomeId: string; imageBase64: string }
  | { phase: "GENERATED"; lastOutcomeId: string; lastImageBase64: string }
  | { phase: "ERROR"; message: string };

export function useChatFlow(outcomes: Outcome[]) {
  const { selectedOutcomeId, setSelectedOutcomeId, lastImageData, setLastImageData, hasAttachment, setHasAttachment } = useChat();
  const aui = useAui();
  const [phase, setPhase] = useState<FlowPhase>({ phase: "OUTCOME_SELECTION" });
  const [hasShownWelcome, setHasShownWelcome] = useState(false);

  const pushAssistantMessage = useCallback(
    (content: string | { type: "image"; image: string; filename?: string }) => {
      const parts = typeof content === "string"
        ? [{ type: "text" as const, text: content }]
        : [content];

      aui.thread.append({
        role: "assistant",
        content: parts,
      });
    },
    [aui]
  );

  const pushSystemMessage = useCallback(
    (text: string) => {
      aui.thread.append({
        role: "system",
        content: [{ type: "text", text }],
      });
    },
    [aui]
  );

  const pushLoadingMessage = useCallback(() => {
    aui.thread.append({
      role: "assistant",
      content: [{ type: "text", text: "Generating..." }],
    });
  }, [aui]);

  useEffect(() => {
    if (!hasShownWelcome) {
      pushAssistantMessage(vocabulary.steps.outcome.message);
      setHasShownWelcome(true);
    }
  }, [hasShownWelcome, pushAssistantMessage]);

  useEffect(() => {
    if (selectedOutcomeId && phase.phase === "OUTCOME_SELECTION") {
      pushAssistantMessage(vocabulary.steps.reference.message);
      setPhase({ phase: "IMAGE_UPLOAD", outcomeId: selectedOutcomeId });
    }
  }, [selectedOutcomeId, phase.phase, pushAssistantMessage]);

  useEffect(() => {
    if (hasAttachment && phase.phase === "IMAGE_UPLOAD" && lastImageData) {
      pushAssistantMessage(vocabulary.steps.generate.label);
      setPhase({ phase: "GENERATING", outcomeId: phase.outcomeId, imageBase64: lastImageData });
    }
  }, [hasAttachment, phase.phase, lastImageData, pushAssistantMessage]);

  const handleOutcomeSelect = useCallback(
    (outcomeId: string) => {
      if (outcomeId === selectedOutcomeId) return;
      setSelectedOutcomeId(outcomeId);
      setHasAttachment(false);
      setLastImageData(null);
    },
    [selectedOutcomeId, setSelectedOutcomeId, setHasAttachment, setLastImageData]
  );

  const handleAttachmentChange = useCallback(
    (file: File | null) => {
      if (file) {
        const reader = new FileReader();
        reader.onload = () => {
          const base64 = reader.result as string;
          setLastImageData(base64);
          setHasAttachment(true);
        };
        reader.readAsDataURL(file);
      } else {
        setHasAttachment(false);
        setLastImageData(null);
      }
    },
    [setHasAttachment, setLastImageData]
  );

  const handleReuseImage = useCallback(() => {
    if (lastImageData && selectedOutcomeId) {
      setHasAttachment(true);
    }
  }, [lastImageData, selectedOutcomeId, setHasAttachment]);

  const handleGenerate = useCallback(async () => {
    if (phase.phase !== "GENERATING") return;

    pushLoadingMessage();

    try {
      const result = await fetch("/api/inference", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          imageBase64: phase.imageBase64,
          outcomeId: phase.outcomeId,
        }),
      });

      const data = await result.json();

      if (data.error) {
        setPhase({ phase: "ERROR", message: data.error });
        pushSystemMessage(data.error);
      } else if (data.url) {
        setPhase({
          phase: "GENERATED",
          lastOutcomeId: phase.outcomeId,
          lastImageBase64: phase.imageBase64,
        });
        pushAssistantMessage({
          type: "image",
          image: data.url,
          filename: `generated-${phase.outcomeId}.png`,
        });
        setSelectedOutcomeId(null);
        setHasAttachment(false);
        setLastImageData(null);
      }
    } catch {
      const errorMsg = "Inference failed. Please try again.";
      setPhase({ phase: "ERROR", message: errorMsg });
      pushSystemMessage(errorMsg);
    }
  }, [phase, pushAssistantMessage, pushSystemMessage, pushLoadingMessage, setSelectedOutcomeId, setHasAttachment, setLastImageData]);

  const handleRetry = useCallback(() => {
    if (phase.phase === "ERROR") {
      const outcomeId = selectedOutcomeId;
      if (outcomeId && lastImageData) {
        setPhase({ phase: "GENERATING", outcomeId, imageBase64: lastImageData });
      }
    }
  }, [phase.phase, selectedOutcomeId, lastImageData]);

  const canGenerate = phase.phase === "GENERATING" || (phase.phase === "IMAGE_UPLOAD" && hasAttachment && lastImageData);
  const showGenerateButton = phase.phase === "GENERATING" || phase.phase === "IMAGE_UPLOAD" || phase.phase === "GENERATED";
  const showReuseButton = phase.phase !== "OUTCOME_SELECTION" && lastImageData && !hasAttachment;

  return {
    phase,
    outcomes,
    selectedOutcomeId,
    handleOutcomeSelect,
    handleAttachmentChange,
    handleReuseImage,
    handleGenerate,
    handleRetry,
    canGenerate,
    showGenerateButton,
    showReuseButton,
    lastImageData,
    vocabulary,
  };
}