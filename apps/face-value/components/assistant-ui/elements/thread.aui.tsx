"use client";

import { useAui, useAuiState } from "@assistant-ui/react";
import {
  ThreadPrimitive,
  MessagePrimitive,
  ComposerPrimitive,
  AttachmentPrimitive,
  AuiIf,
} from "@assistant-ui/react";
import { Image } from "./image";
import { useChatFlow } from "../chat-flow";
import type { Outcome } from "@/outcomes";
import { UploadIcon, ArrowUpIcon, XIcon, RefreshCwIcon, ImageIcon } from "lucide-react";

interface ThreadProps {
  outcomes: Outcome[];
}

function SuggestionItem({ outcome, onClick }: { outcome: Outcome; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="w-full text-left px-4 py-3 rounded-lg border border-border bg-background hover:bg-muted/50 transition-colors"
    >
      <p className="font-medium">{outcome.title}</p>
    </button>
  );
}

function AssistantMessage({ outcomeId, onSelectOutcome }: { outcomeId: string | null; onSelectOutcome: (id: string) => void }) {
  const aui = useAui();

  if (!outcomeId) {
    return (
      <MessagePrimitive.Root className="fade-in slide-in-from-bottom-1 animate-in">
        <div className="text-foreground px-2">
          <div className="flex flex-col gap-2">
            {outcomes.map((outcome) => (
              <SuggestionItem
                key={outcome.id}
                outcome={outcome}
                onClick={() => onSelectOutcome(outcome.id)}
              />
            ))}
          </div>
        </div>
      </MessagePrimitive.Root>
    );
  }

  return null;
}

function UploadMessage({ onAttachmentChange, lastImageData }: { onAttachmentChange: (file: File | null) => void; lastImageData: string | null }) {
  return (
    <MessagePrimitive.Root className="fade-in slide-in-from-bottom-1 animate-in">
      <div className="text-foreground px-2">
        <p className="mb-3">Upload a reference image</p>
        <ComposerPrimitive.Root className="w-full">
          <AttachmentPrimitive.Root className="w-full">
            <AttachmentPrimitive.Dropzone
              disabled={false}
              accept="image/*"
              onAttachmentsChange={(files) => onAttachmentChange(files[0] ?? null)}
              className="border-foreground/10 focus-within:border-foreground/25 data-[dragging=true]:border-ring flex w-full cursor-pointer flex-col gap-2 rounded-lg border bg-muted/30 p-4 transition-[border-color] data-[dragging=true]:border-dashed data-[dragging=true]:bg-[color-mix(in_oklab,var(--color-accent)_50%,var(--color-background))]"
            >
              <div className="flex flex-col items-center gap-3 text-center">
                <ImageIcon className="text-muted-foreground size-12" />
                <p className="text-muted-foreground">Drag & drop or click to upload</p>
                <p className="text-xs text-muted-foreground/60">PNG, JPG, WebP up to 512×512</p>
              </div>
              <AttachmentPrimitive.Attachments>
                {({ attachments }) => (
                  <div className="flex gap-2">
                    {attachments.map((attachment) => (
                      <div key={attachment.id} className="relative size-20 rounded-lg overflow-hidden">
                        <img
                          src={attachment.preview ?? ""}
                          alt={attachment.name}
                          className="h-full w-full object-cover"
                        />
                        <button
                          type="button"
                          onClick={() => onAttachmentChange(null)}
                          className="absolute top-1 right-1 size-5 rounded-full bg-black/50 text-white hover:bg-black/70"
                        >
                          <XIcon className="size-3" />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </AttachmentPrimitive.Attachments>
            </AttachmentPrimitive.Dropzone>
          </AttachmentPrimitive.Root>
        </ComposerPrimitive.Root>
      </div>
    </MessagePrimitive.Root>
  );
}

function GenerateMessage({
  onGenerate,
  onReuseImage,
  canGenerate,
  showReuseButton,
  lastImageData,
  isGenerating,
}: {
  onGenerate: () => void;
  onReuseImage: () => void;
  canGenerate: boolean;
  showReuseButton: boolean;
  lastImageData: string | null;
  isGenerating: boolean;
}) {
  return (
    <MessagePrimitive.Root className="fade-in slide-in-from-bottom-1 animate-in">
      <div className="text-foreground px-2 flex flex-col gap-3">
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onGenerate}
            disabled={!canGenerate || isGenerating}
            className="flex-1 px-4 py-3 rounded-lg bg-primary text-primary-foreground font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors hover:opacity-90"
          >
            {isGenerating ? (
              <>
                <svg className="size-4 animate-spin mr-2" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Generating…
              </>
            ) : (
              "Generate"
            )}
          </button>
        </div>
        {showReuseButton && lastImageData && (
          <button
            type="button"
            onClick={onReuseImage}
            className="text-sm underline text-muted-foreground hover:text-foreground"
          >
            Reuse previous image
          </button>
        )}
      </div>
    </MessagePrimitive.Root>
  );
}

function ErrorMessage({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <MessagePrimitive.Root className="fade-in slide-in-from-bottom-1 animate-in">
      <div className="text-foreground px-2 flex flex-col gap-2">
        <div className="flex items-center gap-2 text-destructive">
          <svg className="size-5" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="8" x2="12" y2="12" />
            <line x1="12" y1="16" x2="12.01" y2="16" />
          </svg>
          <span>{message}</span>
        </div>
        <button
          type="button"
          onClick={onRetry}
          className="px-4 py-2 rounded-lg border border-destructive text-destructive hover:bg-destructive/10 transition-colors self-start"
        >
          Try again
        </button>
      </div>
    </MessagePrimitive.Root>
  );
}

function ResultMessage({ imageUrl, onRegenerate }: { imageUrl: string; onRegenerate: () => void }) {
  return (
    <MessagePrimitive.Root className="fade-in slide-in-from-bottom-1 animate-in">
      <div className="text-foreground px-2 flex flex-col gap-3">
        <div className="relative rounded-lg overflow-hidden border border-border bg-background">
          <Image image={imageUrl} filename="generated.png" />
        </div>
        <button
          type="button"
          onClick={onRegenerate}
          className="px-4 py-2 rounded-lg bg-primary text-primary-foreground font-medium transition-colors hover:opacity-90 self-start"
        >
          Generate another
        </button>
      </div>
    </MessagePrimitive.Root>
  );
}

export function Thread({ outcomes }: ThreadProps) {
  const {
    phase,
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
  } = useChatFlow(outcomes);

  const isGenerating = phase.phase === "GENERATING";

  return (
    <ThreadPrimitive.Root
      className="aui-root aui-thread-root bg-background flex h-full flex-col"
      style={{
        ["--thread-max-width" as string]: "44rem",
        ["--composer-bg" as string]: "color-mix(in oklab, var(--color-muted) 30%, transparent)",
        ["--composer-radius" as string]: "1rem",
        ["--composer-padding" as string]: "8px",
      }}
    >
      <ThreadPrimitive.Viewport
        turnAnchor="top"
        className="relative flex flex-1 flex-col overflow-x-auto overflow-y-scroll scroll-smooth"
      >
        <div className="mx-auto flex w-full max-w-(--thread-max-width) flex-1 flex-col px-4 pt-4">
          <div className="mb-14 flex flex-col gap-y-6 empty:hidden">
            <ThreadPrimitive.Messages>
              {() => (
                <>
                  <AuiIf condition={() => phase.phase === "OUTCOME_SELECTION"}>
                    <AssistantMessage outcomeId={selectedOutcomeId} onSelectOutcome={handleOutcomeSelect} />
                  </AuiIf>
                  <AuiIf condition={() => phase.phase === "IMAGE_UPLOAD"}>
                    <UploadMessage onAttachmentChange={handleAttachmentChange} lastImageData={lastImageData} />
                  </AuiIf>
                  <AuiIf condition={() => showGenerateButton && (phase.phase === "GENERATING" || phase.phase === "IMAGE_UPLOAD" || phase.phase === "GENERATED")}>
                    <GenerateMessage
                      onGenerate={handleGenerate}
                      onReuseImage={handleReuseImage}
                      canGenerate={canGenerate}
                      showReuseButton={showReuseButton}
                      lastImageData={lastImageData}
                      isGenerating={isGenerating}
                    />
                  </AuiIf>
                  <AuiIf condition={() => phase.phase === "ERROR"}>
                    <ErrorMessage message={phase.message} onRetry={handleRetry} />
                  </AuiIf>
                  <AuiIf condition={() => phase.phase === "GENERATED"}>
                    <ResultMessage imageUrl={phase.lastImageBase64} onRegenerate={handleGenerate} />
                  </AuiIf>
                </>
              )}
            </ThreadPrimitive.Messages>
          </div>

          <ThreadPrimitive.ViewportFooter className="aui-thread-viewport-footer bg-background flex flex-col gap-4 overflow-visible pb-4 sticky bottom-0 mt-auto rounded-t-(--composer-radius)">
            <ThreadPrimitive.ScrollToBottom />
          </ThreadPrimitive.ViewportFooter>
        </div>
      </ThreadPrimitive.Viewport>
    </ThreadPrimitive.Root>
  );
}