import { requestSelectedOutcome } from "./requestSelectedOutcome"
import type { PublicOutcome } from "@/outcomes"

export function initialMessage(outcomes: PublicOutcome[] = []) {
  return requestSelectedOutcome(outcomes)
}