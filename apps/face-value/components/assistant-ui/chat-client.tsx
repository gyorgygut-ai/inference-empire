"use client"

import { useEffect } from "react"
import { RuntimeProvider } from "./runtime-provider"
import {
  useAui,
  useAuiState,
  ThreadPrimitive,
  ComposerPrimitive,
  AttachmentPrimitive,
} from "@assistant-ui/react"
import { ImageIcon, XIcon } from "lucide-react"
import { vocabulary } from "@/lib/vocabulary"
import type { PublicOutcome } from "@/outcomes"
import { useImageGeneration } from "./image-generation"
import { MessageSwitch } from "./message-switch"

export function ChatClient({ outcomes }: { outcomes: PublicOutcome[] }) {
  return (
    <RuntimeProvider
      suggestions={outcomes}
      childrenFn={() => <RootAssistantUiComponent outcomes={outcomes} />}
    />
  )
}

export function RootAssistantUiComponent({
  outcomes,
}: {
  outcomes: PublicOutcome[]
}) {
  const aui = useAui()
  const messages = useAuiState((s) => s.thread.messages)
  const threadReady = useAuiState((s) => !s.thread.isLoading)
  const attachments = useAuiState((s) => s.thread.composer.attachments)
  const referenceFile = attachments.find((a) => a.type === "image" && a.file)?.file ?? null

  const { selectedOutcome, result, isPending, canGenerate, onSelectOutcome, onGenerate } =
    useImageGeneration(outcomes, referenceFile)

  useEffect(() => {
    if (!threadReady || messages.length !== 0) { return }
    aui.thread.append({
      role: "assistant",
      content: [{ type: "text", text: vocabulary.messages.selectOutcome }],
      metadata: { custom: { type: "select-outcome" } },
    })
  }, [threadReady, messages.length, aui])

  return (
    <ThreadPrimitive.Root className="h-full flex flex-col">
      <ThreadPrimitive.Viewport className="flex-1 overflow-y-auto">
        <ThreadPrimitive.Messages>
          {({ message }) => (
            <MessageSwitch
              message={message}
              outcomes={outcomes}
              selectedOutcome={selectedOutcome}
              isPending={isPending}
              canGenerate={canGenerate}
              onSelectOutcome={onSelectOutcome}
              onGenerate={onGenerate}
              result={result}
            />
          )}
        </ThreadPrimitive.Messages>
      </ThreadPrimitive.Viewport>
      <UploadComposer />
    </ThreadPrimitive.Root>
  )
}

function UploadComposer() {
  const aui = useAui()
  const attachments = useAuiState((s) => s.thread.composer.attachments)
  const messages = useAuiState((s) => s.thread.messages)

  useEffect(() => {
    const picked = attachments.some((a) => a.type === "image" && a.file)
    if (!picked) { return }
    const exists = messages.some(
      (m) => (m.metadata as { custom?: { type?: string } } | undefined)?.custom?.type === "request-inference",
    )
    if (!exists) {
      aui.thread.append({
        role: "assistant",
        content: [{ type: "text", text: vocabulary.messages.requestInference }],
        metadata: { custom: { type: "request-inference" } },
      })
    }
  }, [attachments, messages, aui])

  return (
    <ComposerPrimitive.AttachmentDropzone className="rounded-xl border-2 border-dashed border-border data-[dragging]:border-primary data-[dragging]:bg-primary/5">
      <ComposerPrimitive.Root className="p-2">
        <ComposerPrimitive.Attachments>
          {({ attachment }) => {
            if (attachment.type !== "image") { return null }
            return (
              <AttachmentPrimitive.Root className="flex items-center gap-2 rounded-lg border p-2">
                <AttachmentPrimitive.unstable_Thumb className="flex size-10 items-center justify-center overflow-hidden rounded bg-muted text-xs">
                  <ImageIcon className="size-4" />
                </AttachmentPrimitive.unstable_Thumb>
                <span className="min-w-0 flex-1 truncate text-sm">
                  <AttachmentPrimitive.Name />
                </span>
                <AttachmentPrimitive.Remove className="ml-auto rounded-full p-1 hover:bg-muted">
                  <XIcon className="size-3" />
                </AttachmentPrimitive.Remove>
              </AttachmentPrimitive.Root>
            )
          }}
        </ComposerPrimitive.Attachments>
        <ComposerPrimitive.AddAttachment className="mt-2 inline-block cursor-pointer rounded border px-3 py-1 text-sm hover:bg-muted">
          {vocabulary.messages.uploadReference}
        </ComposerPrimitive.AddAttachment>
      </ComposerPrimitive.Root>
    </ComposerPrimitive.AttachmentDropzone>
  )
}
