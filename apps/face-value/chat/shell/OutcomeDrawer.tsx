"use client"

import React from "react"
import { BottomDrawer } from "@inference/ui/components/BottomDrawer"
import { vocabulary } from "@/chat/vocabulary/en"
import { useChatContext } from "@/chat/contexts"
import { findLastToolCall } from "@/chat/findLastToolCall"
import { PresentOutcomeOptions } from "@/chat/tools/presentOutcomeOptions"

export const OutcomeDrawer = () => {
  const chat = useChatContext()
  const outcomeCall = findLastToolCall(chat.messages, "presentOutcomeOptions")
  const open =
    outcomeCall?.type === "tool-call" &&
    outcomeCall.name === "presentOutcomeOptions" &&
    outcomeCall.state === "input-complete"

  return (
    <BottomDrawer label={vocabulary.messages.outcomesAria} open={open}>
      {open && outcomeCall?.type === "tool-call" && outcomeCall.name === "presentOutcomeOptions" ? (
        <PresentOutcomeOptions inDrawer part={outcomeCall} />
      ) : null}
    </BottomDrawer>
  )
}
