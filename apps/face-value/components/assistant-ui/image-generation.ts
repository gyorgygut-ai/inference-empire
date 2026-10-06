"use client"

import { useState, useTransition } from "react"
import { useAui } from "@assistant-ui/react"
import type { PublicOutcome } from "@/outcomes"
import { generateImage } from "@/app/actions/generate"
import { vocabulary } from "@/messages/vocabulary"

export function useImageGeneration(
  outcomes: PublicOutcome[],
  referenceFile: File | null,
) {
  const aui = useAui()
  const [selectedOutcome, setSelectedOutcome] = useState<PublicOutcome | null>(null)
  const [result, setResult] = useState<string | null>(null)
  const [isPending, startTransition] = useTransition()

  const canGenerate = !!selectedOutcome && !!referenceFile

  const onSelectOutcome = (id: string) => {
    const outcome = outcomes.find((o) => o.id === id) ?? null
    setSelectedOutcome(outcome)
    setResult(null)
    const messages = aui.thread.getState().messages
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

  const onGenerate = async () => {
    if (!selectedOutcome || !referenceFile || isPending) { return }

    aui.thread.append({
      role: "assistant",
      content: [{ type: "text", text: vocabulary.messages.busy }],
      metadata: { custom: { type: "busy" } },
    })

    startTransition(async () => {
      try {
        const res = await generateImage(selectedOutcome.id, referenceFile)
        if (res.status === "rejected") {
          aui.thread.append({
            role: "assistant",
            content: [{ type: "text", text: vocabulary.messages.rejected }],
            metadata: { custom: { type: "rejected" } },
          })
          return
        }
        setResult(res.presignedUrl)
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
      }
    })
  }

  return { selectedOutcome, result, isPending, canGenerate, onSelectOutcome, onGenerate }
}