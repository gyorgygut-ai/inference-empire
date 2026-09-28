"use client"

import { useEffect, useState } from "react"
import { RuntimeProvider } from "./runtime-provider"
import { useAui, useAuiState } from "@assistant-ui/react"
import { vocabulary } from "@/lib/vocabulary"
import { generateImage } from "@/app/actions/generate"

export function ChatClient({ outcomes }: { outcomes: { id: string; title: string }[] }) {
  return (
    <RuntimeProvider>
      <InnerChat outcomes={outcomes} />
    </RuntimeProvider>
  )
}

function InnerChat({ outcomes }: { outcomes: { id: string; title: string }[] }) {
  const aui = useAui()
  const messages = useAuiState((s) => s.thread.messages)
  const threadReady = useAuiState((s) => {
    const t = s.thread as unknown as { id?: string }
    return !!t.id
  })
  const [selectedOutcome, setSelectedOutcome] = useState<string | null>(null)
  const [referenceFile, setReferenceFile] = useState<File | null>(null)
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    if (!threadReady || messages.length !== 0) { return }
    aui.thread.append({
      role: "assistant",
      content: [{ type: "text", text: vocabulary.steps.outcome.message }]
    })
  }, [threadReady, messages.length])

  useEffect(() => {
    if (!threadReady || !selectedOutcome) { return }
    const exists = messages.find((m) => (m.content?.[0] as unknown as { text?: string })?.text?.includes(vocabulary.steps.reference.message))
    if (!exists) {
      aui.thread.append({
        role: "assistant",
        content: [{ type: "text", text: vocabulary.steps.reference.message }]
      })
    }
  }, [threadReady, selectedOutcome, messages])

  useEffect(() => {
    if (!threadReady || !referenceFile) { return }
    const exists = messages.find((m) => (m.content?.[0] as unknown as { text?: string })?.text?.includes(vocabulary.steps.generate.label))
    if (!exists) {
      aui.thread.append({
        role: "assistant",
        content: [{ type: "text", text: "Ready to generate" }]
      })
    }
  }, [threadReady, referenceFile, messages])

  const handleGenerate = async () => {
    if (!threadReady || !selectedOutcome || !referenceFile) {
      return
    }
    setGenerating(true)
    aui.thread.append({ role: "assistant", content: [{ type: "text", text: "Generating…" }] })
    try {
      const result = await generateImage(selectedOutcome, referenceFile)
      aui.thread.append({
        role: "assistant",
        content: [{ type: "image", image: result.dataUrl }]
      })
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Error"
      aui.thread.append({ role: "assistant", content: [{ type: "text", text: msg }] })
    } finally {
      setGenerating(false)
    }
  }

  return (
    <div className="h-full flex flex-col">
      <div />
      <div className="p-4 border-t">
        {!selectedOutcome && (
          <div className="flex gap-2 flex-wrap">
            {outcomes.map((o) => (
              <button key={o.id} onClick={() => setSelectedOutcome(o.id)} className="px-3 py-1 rounded border">
                {o.title}
              </button>
            ))}
          </div>
        )}
        {selectedOutcome && (
          <input type="file" accept="image/*" onChange={(e) => setReferenceFile(e.target.files?.[0] || null)} />
        )}
        <button disabled={!selectedOutcome || !referenceFile || generating || !threadReady} onClick={handleGenerate} className="mt-2 px-4 py-2 bg-primary text-white rounded">
          {vocabulary.steps.generate.label}
        </button>
      </div>
    </div>
  )
}
