"use client";

import React from "react";
import { fetchServerSentEvents, useGenerateImage } from "@tanstack/ai-react";
import { useChatContext } from "./chat-hook";
import { MessageOutcomeSuggestions } from "./messages/MessageOutcomeSuggestions";
import { vocabulary } from "@/messages";
import type { PublicOutcome } from "@/outcomes/outcomes";

type ReferenceImage = { base64: string; mimeType: string };

const readFileAsData = (file: File): Promise<ReferenceImage> =>
  new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onerror = () => reject(new Error("Reference image unreadable"));
    reader.onload = () => {
      const url = String(reader.result ?? "");
      const match = /^data:([\w/-]+);base64,(.+)$/.exec(url);
      if (!match) {
        reject(new Error("Reference image unreadable"));
        return;
      }
      resolve({ base64: match[2], mimeType: match[1] });
    };
    reader.readAsDataURL(file);
  });

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

  const outcomes = ((messages[0]?.metadata as { outcomes?: PublicOutcome[] } | undefined)?.outcomes ?? []);

  const selectedOutcomeId = [...messages].reverse().reduce<string | undefined>((found, m) => {
    if (found || m.role !== "user") {
      return found;
    }
    const textPart = m.parts?.find((p) => p.type === "text");
    const content = (textPart as { content?: string } | undefined)?.content;
    const match = outcomes.find(
      (o) => content === vocabulary.messages.userPickedOutcome.replace("{title}", o.title),
    );
    return match?.id ?? found;
  }, undefined);

  const reference = [...messages].reverse().reduce<ReferenceImage | undefined>((found, m) => {
    if (found || m.role !== "user") {
      return found;
    }
    const imagePart = m.parts?.find((p) => p.type === "image") as
      | { source?: { type: string; value?: unknown; mimeType?: string } }
      | undefined;
    const source = imagePart?.source;
    if (!source || typeof source.value !== "string") {
      return found;
    }
    if (source.type === "data") {
      return { base64: source.value, mimeType: source.mimeType ?? "image/png" };
    }
    return found;
  }, undefined);

  const hasResult = messages.some((m) =>
    m.parts?.some(
      (p) =>
        p.type === "text" &&
        ((p as { content?: string }).content === vocabulary.messages.fulfilled ||
          (p as { content?: string }).content === vocabulary.messages.rejected),
    ),
  );

  const { generate, isLoading } = useGenerateImage({
    connection: fetchServerSentEvents("/api/image"),
    onResult: async (result) => {
      const url = result.images[0]?.url;
      if (!url) {
        await append({
          id: crypto.randomUUID(),
          role: "assistant",
          parts: [{ type: "text", content: vocabulary.messages.rejected }],
        });
        return;
      }
      await append({
        id: crypto.randomUUID(),
        role: "assistant",
        parts: [
          { type: "text", content: vocabulary.messages.fulfilled },
          { type: "image", source: { type: "url", value: url } },
        ],
      });
    },
    onError: async () => {
      await append({
        id: crypto.randomUUID(),
        role: "assistant",
        parts: [{ type: "text", content: vocabulary.messages.rejected }],
      });
    },
  });

  const showOutcomeSuggestions = !selectedOutcomeId && !hasResult && !isLoading;
  const showAttachmentPrompt = Boolean(selectedOutcomeId) && !reference && !hasResult && !isLoading;
  const showRequestInference = Boolean(selectedOutcomeId && reference) && !hasResult && !isLoading;

  const handleOutcomeSelect = async (id: string) => {
    const outcome = outcomes.find((o) => o.id === id);
    if (!outcome || isLoading) {
      return;
    }
    const content = vocabulary.messages.userPickedOutcome.replace("{title}", outcome.title);
    await append({
      id: crypto.randomUUID(),
      role: "user",
      parts: [{ type: "text", content }],
    });
    await append({
      id: crypto.randomUUID(),
      role: "assistant",
      parts: [{ type: "text", content: vocabulary.messages.uploadReference }],
    });
  };

  const handleImageUpload = async (file: File) => {
    if (isLoading) {
      return;
    }
    const data = await readFileAsData(file);
    await append({
      id: crypto.randomUUID(),
      role: "user",
      parts: [{ type: "image", source: { type: "data", value: data.base64, mimeType: data.mimeType } }],
    });
    await append({
      id: crypto.randomUUID(),
      role: "assistant",
      parts: [{ type: "text", content: vocabulary.messages.requestInference }],
    });
  };

  const handleRequestInference = async () => {
    if (!selectedOutcomeId || !reference || isLoading) {
      return;
    }
    await append({
      id: crypto.randomUUID(),
      role: "assistant",
      parts: [{ type: "text", content: vocabulary.messages.working }],
    });
    await generate({
      prompt: [
        { type: "text", content: selectedOutcomeId },
        { type: "image", source: { type: "data", value: reference.base64, mimeType: reference.mimeType } },
      ],
      modelOptions: { outcomeId: selectedOutcomeId },
    });
  };

  return (
    <div className="h-full flex flex-col">
      <Messages />

      {showOutcomeSuggestions && (
        <MessageOutcomeSuggestions
          outcomes={outcomes}
          onSelect={handleOutcomeSelect}
          disabled={isLoading}
        />
      )}

      {showAttachmentPrompt && (
        <div className="mb-4 animate-in fade-in-50 slide-in-from-bottom-2 duration-500 bg-surface italic rounded-xl p-4" aria-labelledby="uploadReference">
          <span id="uploadReference" className="sr-only">{vocabulary.messages.uploadReference}</span>
          {vocabulary.messages.uploadReference}
          <AttachmentUpload onUpload={handleImageUpload} />
        </div>
      )}

      {showRequestInference && (
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
