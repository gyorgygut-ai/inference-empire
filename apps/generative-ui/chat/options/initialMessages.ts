import { assistantMessagePromptForOutcome } from "../messages/ask-for-outcome"

export function initialChatMessages() {
  return [assistantMessagePromptForOutcome()]
}
