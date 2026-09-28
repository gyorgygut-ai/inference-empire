"use client"

import { useEffect, useState } from "react"
import { RuntimeProvider } from "./runtime-provider"
import {
  useAui,
  useAuiState,
  ThreadPrimitive,
  MessagePrimitive,
  ComposerPrimitive,
  AttachmentPrimitive,
} from "@assistant-ui/react"
import { ImageIcon, XIcon } from "lucide-react"
import { vocabulary } from "@/lib/vocabulary"
import { generateImage } from "@/app/actions/generate"
import type { PublicOutcome } from "@/outcomes"
import { MessageOutcomeSelect } from "./messages/MessageOutcomeSelect"
import { MessageUploadReference } from "./messages/MessageUploadReference"
import { MessageRequestInference } from "./messages/MessageRequestInference"
import { MessageBusy } from "./messages/MessageBusy"
import { MessageRejected } from "./messages/MessageRejected"
import { MessageDone } from "./messages/MessageDone"

export function ChatClient({ outcomes }: { outcomes: PublicOutcome[] }) {
  return (
    <RuntimeProvider
      suggestions={outcomes}
      childrenFn={() => <NonNegotiableRootAssistantUiComponent outcomes={outcomes} />}
    />
  )
}

export function NonNegotiableRootAssistantUiComponent({
  outcomes,
}: {
  outcomes: PublicOutcome[]
}) {
  const aui = useAui()
  const messages = useAuiState((s) => s.thread.messages)
  const threadReady = useAuiState((s) => !s.thread.isLoading)
  const attachments = useAuiState((s) => s.thread.composer.attachments)
  const [selectedOutcome, setSelectedOutcome] = useState<PublicOutcome | null>(null)
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState<string | null>(null)

  const referenceFile = attachments.find((a) => a.type === "image" && a.file)?.file ?? null

  useEffect(() => {
    if (!threadReady || messages.length !== 0) { return }
    aui.thread.append({
      role: "assistant",
      content: [{ type: "text", text: vocabulary.messages.selectOutcome }],
      metadata: { custom: { type: "select-outcome" } },
    })
  }, [threadReady, messages.length, aui])

  const handleSelectOutcome = (id: string) => {
    if (!threadReady) { return }
    const outcome = outcomes.find((o) => o.id === id) ?? null
    setSelectedOutcome(outcome)
    setResult(null)
    const exists = messages.some(
      (m) => (m.metadata as { custom?: { type?: string } } | undefined)?.custom?.type === "upload-reference",
    )
    if (!exists) {
      aui.thread.append({
        role: "assistant",
        content: [{ type: "text", text: vocabulary.messages.uploadReference }],
        metadata: { custom: { type: "upload-reference" } },
      })
    }
  }

  const handleGenerate = async () => {
    if (!selectedOutcome || !referenceFile || generating) { return }
    setGenerating(true)
    aui.thread.append({
      role: "assistant",
      content: [{ type: "text", text: vocabulary.messages.busy }],
      metadata: { custom: { type: "busy" } },
    })
    try {
      const res = await generateImage(selectedOutcome.id, referenceFile)
      setResult(res.dataUrl)
      aui.thread.append({
        role: "assistant",
        content: [{ type: "text", text: vocabulary.messages.done }],
        metadata: { custom: { type: "done" } },
      })
    } catch {
      aui.thread.append({
        role: "assistant",
        content: [{ type: "text", text: vocabulary.messages.rejected }],
        metadata: { custom: { type: "rejected" } },
      })
    } finally {
      setGenerating(false)
    }
  }

  return (
    <ThreadPrimitive.Root className="h-full flex flex-col">
      <ThreadPrimitive.Viewport className="flex-1 overflow-y-auto">
        <ThreadPrimitive.Messages>
          {({ message }) => {
            const meta = message.metadata as { custom?: { type?: string } } | undefined
            if (meta?.custom?.type === "select-outcome") {
              return (
                <MessageOutcomeSelect
                  outcomes={outcomes}
                  selectedId={selectedOutcome?.id ?? null}
                  onSelect={handleSelectOutcome}
                />
              )
            }
            if (meta?.custom?.type === "upload-reference") {
              return <MessageUploadReference />
            }
            if (meta?.custom?.type === "request-inference") {
              return (
                <MessageRequestInference
                  generating={generating}
                  canGenerate={!!selectedOutcome && !!referenceFile}
                  onGenerate={handleGenerate}
                />
              )
            }
            if (meta?.custom?.type === "busy" && selectedOutcome) {
              return <MessageBusy width={selectedOutcome.width} height={selectedOutcome.height} />
            }
            if (meta?.custom?.type === "rejected") {
              return <MessageRejected />
            }
            if (meta?.custom?.type === "done" && result && selectedOutcome) {
              return (
                <MessageDone image={result} width={selectedOutcome.width} height={selectedOutcome.height} />
              )
            }
            return (
              <MessagePrimitive.Root className="mb-4">
                <MessagePrimitive.Parts
                  components={{
                    Text: ({ text }) => <p className="mb-2">{text}</p>,
                  }}
                />
                <MessagePrimitive.Error />
              </MessagePrimitive.Root>
            )
          }}
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
