"use client"

import React from "react"
import { BottomDrawer } from "@inference/ui/components/BottomDrawer"
import { vocabulary } from "@/chat/vocabulary/en"
import { chatOptions } from "@/chat/options"
import { useChatContext } from "@/chat/contexts"
import { findLastToolCall } from "@/chat/findLastToolCall"
import { PresentOutcomeOptions } from "@/chat/tools/presentOutcomeOptions"
import { PresentImageUpload } from "@/chat/tools/presentImageUpload"
import type { LayoutProps } from "@tanstack/ai-react/ui"

type FlowDrawersProps = Pick<LayoutProps<typeof chatOptions>, "Messages" | "Interrupts" | "Queue">

export const FlowDrawers = ({ Messages, Interrupts, Queue }: FlowDrawersProps) => {
  const chat = useChatContext()
  const outcomeCall = findLastToolCall(chat.messages, "presentOutcomeOptions")
  const uploadCall = findLastToolCall(chat.messages, "presentImageUpload")
  const outcomeIsPending =
    outcomeCall?.type === "tool-call" &&
    outcomeCall.name === "presentOutcomeOptions" &&
    outcomeCall.state === "input-complete"
  const uploadIsPending =
    uploadCall?.type === "tool-call" &&
    uploadCall.name === "presentImageUpload" &&
    uploadCall.state === "input-complete"

  return (
    <>
      <div className="flex flex-col gap-6">
        <Messages />
        <Interrupts />
        <Queue />
      </div>
      <BottomDrawer label={vocabulary.messages.outcomesAria} open={outcomeIsPending}>
        {outcomeIsPending &&
        outcomeCall?.type === "tool-call" &&
        outcomeCall.name === "presentOutcomeOptions" ? (
          <PresentOutcomeOptions inDrawer part={outcomeCall} />
        ) : null}
      </BottomDrawer>
      <BottomDrawer label={vocabulary.messages.uploadReference} open={uploadIsPending}>
        {uploadIsPending &&
        uploadCall?.type === "tool-call" &&
        uploadCall.name === "presentImageUpload" ? (
          <PresentImageUpload inDrawer part={uploadCall} />
        ) : null}
      </BottomDrawer>
    </>
  )
}
