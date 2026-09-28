"use client"
import { SuggestionPrimitive, ThreadPrimitive, useAuiState } from "@assistant-ui/react"
import { useChat } from "./chat-context"

function OutcomeSuggestionItem({ onSelect }: { onSelect: (id: string) => void }) {
  const prompt = useAuiState((s) => s.suggestion.prompt)
  const { selectedOutcomeId } = useChat()
  const selected = selectedOutcomeId === prompt

  function handleClick() {
    onSelect(prompt)
  }

  return (
    <SuggestionPrimitive.Trigger
      send={false}
      onClick={handleClick}
      aria-pressed={selected}
      className={selected ? "w-full text-left px-3 py-2 rounded border border-gray-900 bg-gray-100" : "w-full text-left px-3 py-2 rounded border border-gray-200 hover:bg-gray-50"}
    >
      <SuggestionPrimitive.Title />
    </SuggestionPrimitive.Trigger>
  )
}

export default function OutcomeWelcome() {
  const { setSelectedOutcomeId } = useChat()

  return (
    <div className="p-4 space-y-2">
      <ThreadPrimitive.Suggestions>
        {() => <OutcomeSuggestionItem onSelect={setSelectedOutcomeId} />}
      </ThreadPrimitive.Suggestions>
    </div>
  )
}
