"use client";

import React from "react";
import { uploadFile, fileSourceFromHandle } from "@tanstack/ai";
import { useChatContext } from "./chat-hook";
import { usePublicOutcomes } from "./outcomes-context";
import { MessageOutcomeSuggestions } from "./messages/MessageOutcomeSuggestions";
import { flux2Files } from "@/lib/flux2-files-adapter";
import { vocabulary } from "@/messages";

const AttachmentUpload = ({ onUpload }: { onUpload: (file: File) => void }) => {
  const inputRef = React.useRef<HTMLInputElement>(null);

  return (
    <div className="mt-4">
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) {
            onUpload(file);
          }
          if (inputRef.current) {
            inputRef.current.value = "";
          }
        }}
        className="hidden"
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        className="w-full px-4 py-3 border-2 border-dashed rounded-xl hover:bg-primary/5 transition-colors"
      >
        <div className="flex items-center justify-center gap-2 text-sm text-secondary-foreground">
          <svg className="size-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003 3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          {vocabulary.messages.uploadCta}
        </div>
      </button>
    </div>
  );
};

export const ChatLayout = ({ Messages, Interrupts, Queue }: {
  Messages: React.ComponentType;
  Interrupts: React.ComponentType;
  Queue: React.ComponentType;
}) => {
  const { messages, append } = useChatContext();

  // Derive phase from messages - NO external state
  const lastAssistantMsg = [...messages].reverse().find(m => m.role === "assistant");
  const lastUserMsg = [...messages].reverse().find(m => m.role === "user");

  const hasGenerateImageToolCall = lastAssistantMsg?.parts?.some(p => p.type === "tool-call" && p.name === "generateImage");
  const hasGenerateImageResult = lastAssistantMsg?.parts?.some(p => p.type === "tool-result" && p.toolCallId?.includes("generateImage"));

  const showOutcomeSuggestions = lastAssistantMsg?.parts?.some(p =>
    p.type === "text" && p.content?.includes(vocabulary.messages.selectOutcome)
  ) && !hasGenerateImageToolCall && !hasGenerateImageResult;

  const showAttachmentPrompt = lastAssistantMsg?.parts?.some(p =>
    p.type === "text" && p.content?.includes(vocabulary.messages.uploadReference)
  ) && !hasGenerateImageToolCall && !hasGenerateImageResult && !lastUserMsg?.parts?.some(p => p.type === "image");

  const showRequestInference = lastAssistantMsg?.parts?.some(p =>
    p.type === "text" && p.content?.includes(vocabulary.messages.requestInference)
  ) && !hasGenerateImageToolCall && !hasGenerateImageResult;

  // Extract selected outcome from user messages
  const publicOutcomes = usePublicOutcomes();
  const selectedOutcomeId = [...messages].reverse().reduce<string | undefined>((found, m) => {
    if (found || m.role !== "user") {
      return found;
    }
    const textPart = m.parts?.find(p => p.type === "text");
    const content = (textPart as { content?: string } | undefined)?.content;
    const match = publicOutcomes.find(
      (o) => content === vocabulary.messages.userPickedOutcome.replace("{title}", o.title),
    );
    return match?.id ?? found;
  }, undefined);

  const handleOutcomeSelect = (id: string) => {
    const outcome = publicOutcomes.find((o) => o.id === id);
    if (!outcome) { return; }

    const content = vocabulary.messages.userPickedOutcome.replace("{title}", outcome.title);
    append({
      role: "user",
      content,
      parts: [{ type: "text", content }],
    });
    append({
      role: "assistant",
      content: vocabulary.messages.uploadReference,
      parts: [{ type: "text", content: vocabulary.messages.uploadReference }],
    });
  };

  const handleImageUpload = async (file: File) => {
    const handle = await uploadFile({ adapter: flux2Files, input: file });
    append({
      role: "user",
      content: file.name,
      parts: [{ type: "image", source: fileSourceFromHandle(handle) }],
    });
    append({
      role: "assistant",
      content: vocabulary.messages.requestInference,
      parts: [{ type: "text", content: vocabulary.messages.requestInference }],
    });
  };

  const handleRequestInference = () => {
    if (!selectedOutcomeId) { return { }; }
    const imagePart = lastUserMsg?.parts?.find(p => p.type === "image");
    const referenceFileId = imagePart?.source?.type === "file" ? imagePart.source.value : null;
    if (!referenceFileId) { return { }; }
    const outcome = publicOutcomes.find((o) => o.id === selectedOutcomeId);
    if (!outcome) { return { }; }

    append({
      role: "assistant",
      content: "",
      parts: [{
        type: "tool-call",
        name: "generateImage",
        id: crypto.randomUUID(),
        state: "awaiting-input",
        arguments: JSON.stringify({
          outcomeId: selectedOutcomeId,
          referenceFileId,
          width: outcome.width,
          height: outcome.height,
        }),
      }],
    });
  };

  return (
    <div className="h-full flex flex-col">
      <Messages />

      {showOutcomeSuggestions && (
        <MessageOutcomeSuggestions
          outcomes={publicOutcomes}
          onSelect={handleOutcomeSelect}
          disabled={false}
        />
      )}

      {showAttachmentPrompt && (
        <div className="mb-4 animate-in fade-in-50 slide-in-from-bottom-2 duration-500 bg-surface italic rounded-xl p-4" aria-labelledby="uploadReference">
          <span id="uploadReference" className="sr-only">{vocabulary.messages.uploadReference}</span>
          {vocabulary.messages.uploadReference}
          <AttachmentUpload onUpload={handleImageUpload} />
        </div>
      )}

      {showRequestInference && selectedOutcomeId && (
        <div className="animate-in fade-in-50 slide-in-from-bottom-2 duration-300">
          <button
            type="button"
            onClick={handleRequestInference}
            aria-labelledby="requestInference"
            className="my-2 px-4 py-3 bg-primary text-primary-foreground rounded w-full"
          >
            <span id="requestInference" className="sr-only">{vocabulary.messages.requestInference}</span>
            {vocabulary.messages.requestInference}
          </button>
        </div>
      )}

      <Interrupts />
      <Queue />
    </div>
  );
};
