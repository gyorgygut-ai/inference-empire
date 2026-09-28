"use client";

import { useCallback, useMemo } from "react";
import { useAui, useAuiState } from "@assistant-ui/react";
import { useChat } from "./chat-context";
import { useInferenceRuntime } from "./chat-adapter";
import { vocabulary } from "@/app/vocabulary";
import type { Outcome } from "@/outcomes";

export function useChatFlow(outcomes: Outcome[]) {
  const {
    selectedOutcomeId,
    setSelectedOutcomeId,
    lastImageData,
    setLastImageData,
    hasAttachment,
    setHasAttachment,
  } = useChat();
  const { triggerInference } = useInferenceRuntime();
  const aui = useAui();
  const messages = useAuiState((s) => s.thread.messages);
  const isRunning = useAuiState((s) => s.thread.isRunning);

  const handleOutcomeSelect = useCallback((outcomeId: string) => {
    if (outcomeId === selectedOutcomeId) return;
    const outcome = outcomes.find((o) => o.id === outcomeId);
    if (!outcome) return;

    aui.thread.append({
      role: "user",
      content: [{ type: "text", text: outcome.title }],
    });
    aui.thread.append({
      role: "assistant",
      content: [{ type: "text", text: vocabulary.steps.reference.message }],
    });
    setSelectedOutcomeId(outcomeId);
    setHasAttachment(false);
    setLastImageData(null);
  }, [selectedOutcomeId, outcomes, aui, setSelectedOutcomeId, setHasAttachment, setLastImageData]);

  const handleAttachmentChange = useCallback((file: File | null) => {
    if (!file) {
      setHasAttachment(false);
      setLastImageData(null);
      return;
    }
    if (file.size > 512 * 1024) {
      aui.thread.append({ role: "system", content: [{ type: "text", text: "Image exceeds 512KB limit." }] });
      return;
    }
    if (!file.type.startsWith("image/")) {
      aui.thread.append({ role: "system", content: [{ type: "text", text: "Please select an image file." }] });
      return;
    }

    const reader = new FileReader();
    reader.onload = () => {
      const base64 = reader.result as string;
      aui.thread.append({ role: "user", content: [{ type: "image", image: base64 }] });
      aui.thread.append({
        role: "assistant",
        content: [{ type: "text", text: vocabulary.steps.generate.label }],
      });
      setLastImageData(base64);
      setHasAttachment(true);
    };
    reader.readAsDataURL(file);
  }, [setHasAttachment, setLastImageData, aui]);

  const handleReuseImage = useCallback(() => {
    if (!lastImageData || !selectedOutcomeId) return;
    aui.thread.append({ role: "user", content: [{ type: "image", image: lastImageData }] });
    aui.thread.append({
      role: "assistant",
      content: [{ type: "text", text: vocabulary.steps.generate.label }],
    });
    setHasAttachment(true);
  }, [lastImageData, selectedOutcomeId, setHasAttachment, aui]);

  const handleGenerate = useCallback(async () => {
    if (!selectedOutcomeId || !lastImageData) return;
    await triggerInference();
  }, [selectedOutcomeId, lastImageData, triggerInference]);

  const lastAssistantText = useMemo(() =>
    messages
      .filter((m) => m.role === "assistant")
      .pop()
      ?.content
      .filter((c) => c.type === "text")
      .map((c) => c.text)
      .join(" ") ?? "",
    [messages]
  );

  const showOutcomeSuggestions = !selectedOutcomeId && lastAssistantText === vocabulary.steps.outcome.message;
  const showAttachmentUpload = selectedOutcomeId && !hasAttachment && lastAssistantText === vocabulary.steps.reference.message;
  const showGenerateButton = hasAttachment && !!lastImageData && lastAssistantText === vocabulary.steps.generate.label;
  const showReuseButton = !hasAttachment && !!lastImageData && !!selectedOutcomeId;
  const isGenerating = isRunning;

  return {
    selectedOutcomeId,
    hasAttachment,
    lastImageData,
    handleOutcomeSelect,
    handleAttachmentChange,
    handleReuseImage,
    handleGenerate,
    canGenerate: hasAttachment && !!lastImageData && !!selectedOutcomeId,
    showOutcomeSuggestions,
    showAttachmentUpload,
    showGenerateButton,
    showReuseButton,
    isGenerating,
    vocabulary,
  };
}
