import { requestSelectedOutcome } from "./request-selected-outcome"
import type { PublicOutcome } from "@/outcomes"

export function initialMessage(outcomes: PublicOutcome[] = []) {
  return requestSelectedOutcome(outcomes)
}