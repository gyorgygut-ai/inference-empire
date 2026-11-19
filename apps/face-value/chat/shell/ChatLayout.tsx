"use client"

import React from "react"
import { chatOptions } from "@/chat/options"
import { OutcomeDrawer } from "./OutcomeDrawer"
import { ReferenceImageDrawer } from "./ReferenceImageDrawer"
import type { LayoutProps } from "@tanstack/ai-react/ui"

type ChatLayoutProps = Pick<LayoutProps<typeof chatOptions>, "Messages" | "Interrupts" | "Queue">

export const ChatLayout = ({ Messages, Interrupts, Queue }: ChatLayoutProps) => (
  <div className="relative flex min-h-[calc(100dvh-3rem)] flex-col gap-6">
    <Messages />
    <Interrupts />
    <Queue />
    <OutcomeDrawer />
    <ReferenceImageDrawer />
  </div>
)
