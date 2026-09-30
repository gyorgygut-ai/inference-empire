"use client"

import type { MessageState } from "@assistant-ui/react"
import type { PublicOutcome } from "@/outcomes"
import { MessageOutcomeSelect } from "./messages/MessageOutcomeSelect"
import { MessageUploadReference } from "./messages/MessageUploadReference"
import { MessageRequestInference } from "./messages/MessageRequestInference"
import { MessageBusy } from "./messages/MessageBusy"
import { MessageRejected } from "./messages/MessageRejected"
import { MessageDone } from "./messages/MessageDone"

export function MessageSwitch({
  message,
  outcomes,
  selectedOutcome,
  isPending,
  canGenerate,
  onSelectOutcome,
  onGenerate,
  result,
}: {
  message: MessageState
  outcomes: PublicOutcome[]
  selectedOutcome: PublicOutcome | null
  isPending: boolean
  canGenerate: boolean
  onSelectOutcome: (id: string) => void
  onGenerate: () => void
  result: string | null
}) {
  const meta = message.metadata as { custom?: { type?: string } } | undefined
  const type = meta?.custom?.type

  if (type === "select-outcome") {
    return (
      <MessageOutcomeSelect
        outcomes={outcomes}
        selectedId={selectedOutcome?.id ?? null}
        onSelect={onSelectOutcome}
      />
    )
  }
  if (type === "upload-reference") {
    return <MessageUploadReference />
  }
  if (type === "request-inference") {
    return (
      <MessageRequestInference
        isPending={isPending}
        canGenerate={canGenerate}
        onGenerate={onGenerate}
      />
    )
  }
  if (type === "busy" && selectedOutcome) {
    return <MessageBusy width={selectedOutcome.width} height={selectedOutcome.height} />
  }
  if (type === "rejected") {
    return <MessageRejected />
  }
  if (type === "done" && result && selectedOutcome) {
    return (
      <MessageDone image={result} width={selectedOutcome.width} height={selectedOutcome.height} />
    )
  }

  return null
}