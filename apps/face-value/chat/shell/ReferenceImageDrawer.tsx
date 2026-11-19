"use client"

import React from "react"
import { BottomDrawer } from "@inference/ui/components/BottomDrawer"
import { vocabulary } from "@/chat/vocabulary/en"
import { useChatContext } from "@/chat/contexts"
import { findLastToolCall } from "@/chat/findLastToolCall"
import { PresentImageUpload } from "@/chat/tools/presentImageUpload"

export const ReferenceImageDrawer = () => {
  const chat = useChatContext()
  const uploadCall = findLastToolCall(chat.messages, "presentImageUpload")
  const open =
    uploadCall?.type === "tool-call" &&
    uploadCall.name === "presentImageUpload" &&
    uploadCall.state === "input-complete"

  return (
    <BottomDrawer label={vocabulary.messages.uploadReference} open={open}>
      {open && uploadCall?.type === "tool-call" && uploadCall.name === "presentImageUpload" ? (
        <PresentImageUpload inDrawer part={uploadCall} />
      ) : null}
    </BottomDrawer>
  )
}
