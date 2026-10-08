"use client";

import React from "react";
import { useChatContext } from "./chat-hook";
import { MessageOutcomeSuggestions } from "./messages/MessageOutcomeSuggestions";
import { getPublicOutcomes, getInferenceOutcome } from "@/outcomes";
import { vocabulary } from "@/messages/vocabulary";

export function ChatLayout({ Messages, Interrupts, Queue }: {
  Messages: React.ComponentType;
  Interrupts: React.ComponentType;
  Queue: React.ComponentType;
}) {
  const { messages, append } = useChatContext();

  // Derive phase from messages - NO external state
  const lastAssistantMsg = [...messages].reverse().find(m => m.role === "assistant");
  const lastUserMsg = [...messages].reverse().find(m => m.role === "user");
  
  const hasGenerateImageToolCall = lastAssistantMsg?.parts?.some(p => p.type === "tool-call" && p.name === "generateImage");
  const hasGenerateImageResult = lastAssistantMsg?.parts?.some(p => p.type === "tool-result" && p.toolCallId?.includes("generateImage"));
  
  const showOutcomeSuggestions = lastAssistantMsg?.parts?.some(p => 
    p.type === "text" && p.content?.includes("Select an outcome")
  ) && !hasGenerateImageToolCall && !hasGenerateImageResult;

  const showAttachmentPrompt = lastAssistantMsg?.parts?.some(p => 
    p.type === "text" && p.content?.includes("Upload your photo")
  ) && !hasGenerateImageToolCall && !hasGenerateImageResult && !lastUserMsg?.parts?.some(p => p.type === "image");

  const showRequestInference = lastAssistantMsg?.parts?.some(p => 
    p.type === "text" && p.content?.includes("Let")
  ) && !hasGenerateImageToolCall && !hasGenerateImageResult;

  // Extract selected outcome from messages
  const selectedOutcomeId = lastAssistantMsg?.parts?.find(p => p.type === "tool-call" && p.name === "generateImage")?.input?.outcomeId;

  const handleOutcomeSelect = (id: string) => {
    const outcome = getInferenceOutcome(id);
    if (!outcome) return;
    
    append({
      role: "user",
      content: `I want ${outcome.title}`,
      parts: [{ type: "text", content: `I want ${outcome.title}` }],
    });
    append({
      role: "assistant",
      content: vocabulary.messages.uploadReference,
      parts: [{ type: "text", content: vocabulary.messages.uploadReference }],
    });
  };

  const handleImageUpload = (file: File) => {
    const reader = new FileReader();
    reader.onload = () => {
      append({
        role: "user",
        content: file.name,
        parts: [{ type: "image", source: { type: "data", value: reader.result as string, mimeType: file.type } }],
      });
      append({
        role: "assistant",
        content: vocabulary.messages.requestInference,
        parts: [{ type: "text", content: vocabulary.messages.requestInference }],
      });
    };
    reader.readAsDataURL(file);
  };

  const handleRequestInference = () => {
    if (!selectedOutcomeId) return;
    const imagePart = lastUserMsg?.parts?.find(p => p.type === "image");
    const referenceImage = imagePart?.source?.type === "data" ? imagePart.source.value : null;
    if (!referenceImage) return;
    
    // Convert data URL back to File-like object for the tool
    const file = dataUrlToFile(referenceImage, "reference.jpg");
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
          outcomePrompt: getInferenceOutcome(selectedOutcomeId)?.prompt || "",
          referenceImage: file 
        }),
      }],
    });
  };

  return (
    <div className="h-full flex flex-col">
      <Messages />
      
      {showOutcomeSuggestions && (
        <MessageOutcomeSuggestions 
          outcomes={getPublicOutcomes()} 
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
}

function dataUrlToFile(dataUrl: string, filename: string): File {
  const arr = dataUrl.split(",");
  const mime = arr[0].match(/:(.*?);/)?.[1] || "image/jpeg";
  const bstr = atob(arr[1]);
  let n = bstr.length;
  const u8arr = new Uint8Array(n);
  while (n--) u8arr[n] = bstr.charCodeAt(n);
  return new File([u8arr], filename, { type: mime });
}

function AttachmentUpload({ onUpload }: { onUpload: (file: File) => void }) {
  const inputRef = React.useRef<HTMLInputElement>(null);
  
  return (
    <div className="mt-4">
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) onUpload(file);
          if (inputRef.current) inputRef.current.value = "";
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
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
          </svg>
          Click or drag & drop an image
        </div>
      </button>
    </div>
  );
}
