"use client";

import { useAuiState } from "@assistant-ui/react";
import { MessagePrimitive } from "@assistant-ui/react";
import { ComposerPrimitive, AttachmentPrimitive } from "@assistant-ui/react";
import { Image } from "./image";
import { useChatFlow } from "../chat-flow";
import type { Outcome } from "@/outcomes";
import { XIcon, ImageIcon } from "lucide-react";

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

export function Thread({ outcomes }: ThreadProps) {
  const {
    selectedOutcomeId,
    hasAttachment,
    lastImageData,
    handleOutcomeSelect,
    handleAttachmentChange,
    handleReuseImage,
    handleGenerate,
    canGenerate,
    showOutcomeSuggestions,
    showAttachmentUpload,
    showGenerateButton,
    showReuseButton,
    isGenerating,
    vocabulary,
  } = useChatFlow(outcomes);

  return (
    <div className="aui-root aui-thread-root bg-background flex h-full flex-col">
      <div className="relative flex flex-1 flex-col overflow-x-auto overflow-y-scroll scroll-smooth">
        <div className="mx-auto flex w-full max-w-[44rem] flex-1 flex-col px-4 pt-4">
          <div className="mb-14 flex flex-col gap-y-6 empty:hidden">
            <MessagePrimitive.Root>
              <MessagePrimitive.Parts />
            </MessagePrimitive.Root>
          </div>

          <div className="aui-thread-viewport-footer bg-background flex flex-col gap-4 overflow-visible pb-4 sticky bottom-0 mt-auto rounded-t-[1rem]">
            <ComposerPrimitive.Root className="w-full">
              {showOutcomeSuggestions && (
                <div className="flex flex-col gap-2 mb-4">
                  {outcomes.map((outcome) => (
                    <SuggestionItem key={outcome.id} outcome={outcome} onClick={() => handleOutcomeSelect(outcome.id)} />
                  ))}
                </div>
              )}

              {showAttachmentUpload && (
                <AttachmentPrimitive.Root className="w-full">
                  <ComposerPrimitive.AttachmentDropzone
                    disabled={false}
                    className="border-foreground/10 focus-within:border-foreground/25 data-[dragging=true]:border-ring flex w-full cursor-pointer flex-col gap-2 rounded-lg border bg-muted/30 p-4 transition-[border-color] data-[dragging=true]:border-dashed"
                  >
                    <div className="flex flex-col items-center gap-3 text-center">
                      <ImageIcon className="text-muted-foreground size-12" />
                      <p className="text-muted-foreground">Drag & drop or click to upload</p>
                      <p className="text-xs text-muted-foreground/60">PNG, JPG, WebP up to 512×512</p>
                    </div>
                  </ComposerPrimitive.AttachmentDropzone>
                </AttachmentPrimitive.Root>
              )}

              {(showGenerateButton || showReuseButton) && (
                <div className="flex flex-col gap-2">
                  {showGenerateButton && (
                    <button
                      type="button"
                      onClick={handleGenerate}
                      disabled={!canGenerate || isGenerating}
                      className="flex-1 px-4 py-3 rounded-lg bg-primary text-primary-foreground font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors hover:opacity-90"
                    >
                      {isGenerating ? (
                        <>
                          <svg className="size-4 animate-spin mr-2" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                          </svg>
                          Generating…
                        </>
                      ) : (
                        vocabulary.steps.generate.label
                      )}
                    </button>
                  )}
                  {showReuseButton && lastImageData && (
                    <button
                      type="button"
                      onClick={handleReuseImage}
                      className="text-sm underline text-muted-foreground hover:text-foreground self-center"
                    >
                      Reuse previous image
                    </button>
                  )}
                </div>
              )}

              {hasAttachment && lastImageData && (
                <div className="flex items-center gap-2 p-2 bg-muted/30 rounded-lg">
                  <img src={lastImageData} alt="Reference" className="size-16 rounded-lg object-cover" />
                  <button type="button" onClick={() => handleAttachmentChange(null)} className="size-8 rounded-full bg-black/50 text-white hover:bg-black/70 flex-shrink-0">
                    <XIcon className="size-4" />
                  </button>
                  {showReuseButton && (
                    <button type="button" onClick={handleReuseImage} className="text-sm underline text-muted-foreground hover:text-foreground ml-auto">
                      Reuse
                    </button>
                  )}
                </div>
              )}
            </ComposerPrimitive.Root>
          </div>
        </div>
      </div>
    </div>
  );
}
