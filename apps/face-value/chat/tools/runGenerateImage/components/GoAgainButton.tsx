"use client"

import { useChatContext } from "@/chat/contexts"
import { vocabulary } from "@/chat/vocabulary/en"
import { requestSelectedOutcome } from "@/chat/messages/requestSelectedOutcome"
import { findLastToolCall } from "@/chat/findLastToolCall"

export const GoAgainButton = () => {
  const chat = useChatContext()

  const handleGoAgain = () => {
    const selection = findLastToolCall(chat.messages, "presentOutcomeOptions")
    if (
      selection?.type !== "tool-call" ||
      selection.name !== "presentOutcomeOptions" ||
      !selection.input
    ) {
      return
    }

    chat.setMessages([
      ...chat.messages,
      requestSelectedOutcome(selection.input.outcomes),
    ])
  }

  return (
    <button
      className="rounded-xl bg-primary px-4 py-2 text-primary-foreground"
      onClick={handleGoAgain}
      type="button"
    >
      {vocabulary.messages.goAgain}
    </button>
  )
}
