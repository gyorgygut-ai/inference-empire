"use client"

import { useMemo, useRef, useState } from "react"
import {
  AssistantRuntimeProvider,
  AttachmentPrimitive,
  ComposerPrimitive,
  CompositeAttachmentAdapter,
  MessagePrimitive,
  SimpleImageAttachmentAdapter,
  ThreadPrimitive,
  useAuiState,
  useLocalRuntime,
  type ChatModelAdapter,
  type ChatModelRunOptions,
  type ThreadUserMessage,
} from "@assistant-ui/react"
import { requestOutcome } from "@/app/actions"
import { vocabulary } from "@/app/vocabulary"
import {
  fileFromAttachment,
  submitFlow,
  urlToFile,
} from "./chat-adapter"
import { step2Prompt } from "./chat-flow"

interface OutcomeOption {
  id: string;
  title: string;
}

function ComposerStatus({ selectedId }: { selectedId: string | null }) {
  const isRunning = useAuiState((s) => s.thread.isRunning)
  const attachments = useAuiState((s) => s.thread.composer.attachments)
  if (isRunning) {
    return <p>{vocabulary.image.generating}</p>
  }
  if (!selectedId) {
    return <p>{vocabulary.outcomePicker.missingSelection}</p>
  }
  if (attachments.length === 0) {
    return <p>{vocabulary.outcomePicker.initialAttach}</p>
  }
  return null
}

export default function ChatClient({ outcomes }: { outcomes: OutcomeOption[] }) {
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [lastImageUrl, setLastImageUrl] = useState<string | null>(null)
  const selectedRef = useRef<string | null>(null)

  const chatModel = useMemo<ChatModelAdapter>(
    () => ({
      run: async ({ messages }: ChatModelRunOptions) => {
        const outcomeId = selectedRef.current
        const users = messages.filter((m): m is ThreadUserMessage => m.role === "user")
        const attachment = users[users.length - 1]?.attachments[0]
        const file = attachment ? await fileFromAttachment(attachment) : null
        const mapped = await submitFlow(outcomeId, file, (fd) => requestOutcome(null, fd))
        if (mapped.imageUrl) {
          setLastImageUrl(mapped.imageUrl)
        }
        return { content: mapped.content }
      },
    }),
    [],
  )

  const attachmentAdapter = useMemo(
    () => new CompositeAttachmentAdapter([new SimpleImageAttachmentAdapter()]),
    [],
  )

  const runtime = useLocalRuntime(chatModel, { adapters: { attachments: attachmentAdapter } })

  function selectOutcome(outcome: OutcomeOption) {
    selectedRef.current = outcome.id
    setSelectedId(outcome.id)
    runtime.thread.append({
      role: "user",
      content: [{ type: "text", text: `Selected outcome: ${outcome.title}` }],
    })
    runtime.thread.append({
      role: "assistant",
      content: [{ type: "text", text: step2Prompt(outcome) }],
    })
  }

  async function reuseLastImage() {
    if (!lastImageUrl) {
      return
    }
    const file = await urlToFile(lastImageUrl, "previous.png")
    await runtime.thread.composer.addAttachment(file)
  }

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <div className="flex flex-col h-full">
        <div>
          <h2>{vocabulary.outcomePicker.heading}</h2>
          {outcomes.length === 0 ? (
            <p>{vocabulary.outcomePicker.missingSelection}</p>
          ) : (
            <div>
              {outcomes.map((outcome) => (
                <button
                  key={outcome.id}
                  type="button"
                  aria-pressed={selectedId === outcome.id}
                  onClick={() => selectOutcome(outcome)}
                >
                  {outcome.title}
                </button>
              ))}
            </div>
          )}
          <p>{selectedId ? vocabulary.outcomePicker.selectedHint : vocabulary.outcomePicker.initialPick}</p>
        </div>
        <ThreadPrimitive.Root className="flex-1 overflow-hidden">
          <ThreadPrimitive.Viewport className="h-full overflow-y-auto">
            <ThreadPrimitive.Empty>
              <p>{vocabulary.thread.welcome}</p>
              <p>{vocabulary.outcomePicker.initialAttach}</p>
            </ThreadPrimitive.Empty>
            <ThreadPrimitive.Messages>
              {() => (
                <MessagePrimitive.Root>
                  <MessagePrimitive.Content />
                </MessagePrimitive.Root>
              )}
            </ThreadPrimitive.Messages>
          </ThreadPrimitive.Viewport>
          <ThreadPrimitive.ScrollToBottom>{vocabulary.thread.scrollToBottom}</ThreadPrimitive.ScrollToBottom>
        </ThreadPrimitive.Root>
        {lastImageUrl && <a href={lastImageUrl} download>{vocabulary.image.download}</a>}
        <ComposerPrimitive.Root>
          <ComposerPrimitive.Attachments>
            {() => (
              <AttachmentPrimitive.Root>
                <AttachmentPrimitive.unstable_Thumb />
                <AttachmentPrimitive.Name />
                <AttachmentPrimitive.Remove>{vocabulary.attachment.removeFile}</AttachmentPrimitive.Remove>
              </AttachmentPrimitive.Root>
            )}
          </ComposerPrimitive.Attachments>
          <ComposerPrimitive.AddAttachment>{vocabulary.composer.addAttachment}</ComposerPrimitive.AddAttachment>
          {lastImageUrl && (
            <button type="button" onClick={reuseLastImage}>
              {vocabulary.composer.reusePrevious}
            </button>
          )}
          <ComposerPrimitive.Send>{vocabulary.composer.generate}</ComposerPrimitive.Send>
        </ComposerPrimitive.Root>
        <ComposerStatus selectedId={selectedId} />
      </div>
    </AssistantRuntimeProvider>
  )
}
