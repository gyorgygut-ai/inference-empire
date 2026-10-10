import { requestSelectedOutcome } from "./request-selected-outcome"
import type { PublicOutcome } from "@/outcomes"

export function initialChatMessages(outcomes: PublicOutcome[] = []) {
  return [requestSelectedOutcome(outcomes)]
}
