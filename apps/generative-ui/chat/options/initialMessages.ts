import { assistantMessagePromptForOutcome } from "../messages/ask-for-outcome"
import type { PublicOutcome } from "@/outcomes"

export function initialChatMessages(outcomes: PublicOutcome[] = []) {
  return [assistantMessagePromptForOutcome(outcomes)]
}
